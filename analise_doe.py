#!/usr/bin/env python3
"""Analise estatistica DoE dos protocolos de conectividade IoT (WiFi / LoRaWAN / 6LoWPAN).

Replica a metodologia de Moraes (2019, UFPE) adaptada para a camada de rede/enlace
e para o contexto multi-cloud medico deste projeto. Para cada metrica calcula:

  * Media + Intervalo de Confianca de 95% por protocolo
  * ANOVA de 1 fator (fator = protocolo, alpha = 0.05)
  * Teste post-hoc de Tukey HSD (quais pares diferem)
  * Correlacao de Pearson (r e r^2) entre as metricas

Design of Experiments (fatorial de 1 fator, l^k com r replicacoes):
  - Fator:   protocolo
  - Niveis:  wifi, lorawan, 6lowpan   (k = 3)
  - Replica: 1 janela de tempo (default 5 min); a metrica da replica e a MEDIA
             das mensagens caidas naquela janela (igual "cada amostra = media de
             5 min" da dissertacao). Pegam-se as ultimas r janelas por protocolo.

Fonte de dados: tabela metricas_iot (PostgreSQL / TimescaleDB), campos em JSONB.

Exemplos:
  # Experimento I (operacao normal), ultimas 6 horas, 30 replicas de 5 min:
  python3 analise_doe.py --experimento I --horas 6 --janela 5 --replicas 30 --graficos

  # Experimento II (com falha/failover), intervalo explicito:
  python3 analise_doe.py --experimento II \
      --desde "2026-07-23 12:00" --ate "2026-07-23 14:00" --saida ./saida_expII
"""
import argparse
import os
import sys
import textwrap
from datetime import datetime

# ---- dependencias de terceiros (erro amigavel se faltarem) -------------------
try:
    import numpy as np
    import pandas as pd
    from scipy import stats
    import psycopg2
except ImportError as e:  # pragma: no cover
    sys.exit(
        f"[ERRO] Falta uma dependencia: {e.name}.\n"
        "Instale com:  pip install -r requirements_analise.txt\n"
        "(ou:  pip install psycopg2-binary pandas numpy scipy statsmodels matplotlib)"
    )

# statsmodels (Tukey) e matplotlib (graficos) sao opcionais.
try:
    from statsmodels.stats.multicomp import pairwise_tukeyhsd
    _TEM_TUKEY = True
except ImportError:
    _TEM_TUKEY = False

DSN_PADRAO = os.environ.get(
    "PG_DSN", "dbname=iot_medico user=iot password=iotmestrado host=localhost"
)

# Metricas base lidas do JSONB (nome no banco -> rotulo, unidade, sentido "melhor").
METRICAS = {
    "latencia_ms": ("Latencia", "ms", "menor"),
    "jitter_ms":   ("Jitter", "ms", "menor"),
    "pdr":         ("PDR (taxa de entrega)", "0-1", "maior"),
    "perda_pct":   ("Perda de pacotes", "%", "menor"),
    "rssi":        ("RSSI", "dBm", "maior"),
    "snr":         ("SNR", "dB", "maior"),
    "energia_mah": ("Energia por mensagem", "mAh", "menor"),
}
# perda_pct e derivada de pdr; as demais vem direto do JSONB.
METRICAS_BASE_JSONB = ["latencia_ms", "jitter_ms", "pdr", "rssi", "snr", "energia_mah"]


def parse_args():
    p = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent(__doc__),
    )
    p.add_argument("--dsn", default=DSN_PADRAO, help="DSN do PostgreSQL (ou env PG_DSN)")
    p.add_argument("--experimento", default="I", help="Rotulo do experimento (I, II, ...)")
    p.add_argument("--protocolos", default="wifi,lorawan,6lowpan",
                   help="Lista separada por virgula (default: wifi,lorawan,6lowpan)")
    p.add_argument("--metricas", default="latencia_ms,jitter_ms,pdr,perda_pct,rssi,snr,energia_mah",
                   help="Metricas a analisar (subconjunto de %s)" % ",".join(METRICAS))
    p.add_argument("--janela", type=float, default=5.0,
                   help="Tamanho da janela/amostra em minutos (default: 5)")
    p.add_argument("--replicas", type=int, default=30,
                   help="Nº de janelas (replicas) por protocolo, mais recentes (default: 30)")
    p.add_argument("--min-amostras", type=int, default=3,
                   help="Descarta janelas com menos de N mensagens (default: 3)")
    p.add_argument("--horas", type=float, default=24.0,
                   help="Analisa as ultimas N horas se --desde nao for dado (default: 24)")
    p.add_argument("--desde", default=None, help="Inicio explicito (ex.: '2026-07-23 12:00')")
    p.add_argument("--ate", default=None, help="Fim explicito (ex.: '2026-07-23 14:00')")
    p.add_argument("--cloud", default=None, help="Filtra por cloud de origem (ex.: gcp, aws)")
    p.add_argument("--alpha", type=float, default=0.05, help="Nivel de significancia (default: 0.05)")
    p.add_argument("--saida", default="./saida_doe", help="Diretorio para CSVs/graficos")
    p.add_argument("--graficos", action="store_true", help="Gera graficos PNG (requer matplotlib)")
    return p.parse_args()


def carregar_dados(args):
    """Consulta o banco e devolve um DataFrame com colunas: time, protocolo, <metricas base>."""
    protocolos = [x.strip() for x in args.protocolos.split(",") if x.strip()]
    cols = ", ".join(f"(fields->>'{m}')::float AS {m}" for m in METRICAS_BASE_JSONB)

    where = ["protocolo = ANY(%(protos)s)"]
    params = {"protos": protocolos}
    if args.desde:
        where.append("time >= %(desde)s"); params["desde"] = args.desde
    if args.ate:
        where.append("time <= %(ate)s"); params["ate"] = args.ate
    if not args.desde and not args.ate:
        where.append("time > now() - (%(horas)s || ' hours')::interval")
        params["horas"] = str(args.horas)
    if args.cloud:
        where.append("cloud = %(cloud)s"); params["cloud"] = args.cloud

    sql = (f"SELECT time, protocolo, {cols} FROM metricas_iot "
           f"WHERE {' AND '.join(where)} ORDER BY time")

    print(f"[DB] conectando: {args.dsn.split('password=')[0].strip()} ...", flush=True)
    with psycopg2.connect(args.dsn) as conn:
        df = pd.read_sql_query(sql, conn, params=params)
    print(f"[DB] {len(df)} mensagens carregadas ({', '.join(protocolos)})", flush=True)
    if df.empty:
        sys.exit("[ERRO] Nenhum dado no intervalo/filtro escolhido. Ajuste --horas/--desde/--cloud.")
    df["time"] = pd.to_datetime(df["time"], utc=True)
    return df


def montar_replicas(df, args):
    """Agrega as mensagens em janelas de tempo (replicas) e devolve a media por janela."""
    df = df.copy()
    df["janela"] = df["time"].dt.floor(f"{int(args.janela)}min"
                                       if args.janela.is_integer() else f"{args.janela}min")
    g = df.groupby(["protocolo", "janela"])
    agg = g[METRICAS_BASE_JSONB].mean()
    agg["n_msgs"] = g.size()
    agg = agg.reset_index()
    agg = agg[agg["n_msgs"] >= args.min_amostras]
    # perda de pacotes (%) derivada do PDR medio da janela
    if "pdr" in agg:
        agg["perda_pct"] = (1.0 - agg["pdr"]) * 100.0
    # mantem as ultimas N janelas (replicas) por protocolo
    agg = (agg.sort_values("janela")
              .groupby("protocolo", group_keys=False)
              .tail(args.replicas)
              .reset_index(drop=True))
    return agg


def ic95(x, alpha=0.05):
    """Media e intervalo de confianca (1-alpha) usando t de Student."""
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    n = len(x)
    m = float(np.mean(x)) if n else float("nan")
    if n < 2:
        return m, m, m, n
    se = np.std(x, ddof=1) / np.sqrt(n)
    h = se * stats.t.ppf(1 - alpha / 2.0, n - 1)
    return m, m - h, m + h, n


def analisar_metrica(agg, metrica, protocolos, alpha):
    """Analisa uma metrica com abordagem parametrica e nao-parametrica.

    Devolve (resumo_df, anova_dict, tukey_df, kruskal_dict, mannwhitney_df).
      * Parametrico (Moraes 2019): ANOVA de 1 fator + Tukey HSD.
      * Nao-parametrico (artigo WTF): Kruskal-Wallis + Mann-Whitney pareado.
    """
    grupos, linhas = [], []
    for proto in protocolos:
        vals = agg.loc[agg["protocolo"] == proto, metrica].dropna().values
        if len(vals) == 0:
            continue
        grupos.append((proto, vals))
        m, lo, hi, n = ic95(vals, alpha)
        linhas.append({"protocolo": proto, "n_replicas": n, "media": round(m, 4),
                       "ic95_min": round(lo, 4), "ic95_max": round(hi, 4),
                       "desvio": round(float(np.std(vals, ddof=1)) if n > 1 else 0.0, 4)})
    resumo = pd.DataFrame(linhas)

    # --- Parametrico: ANOVA de 1 fator ---
    anova = {"df": None, "F": None, "p": None}
    if len(grupos) >= 2 and all(len(v) >= 2 for _, v in grupos):
        try:
            F, p = stats.f_oneway(*[v for _, v in grupos])
            if np.isfinite(F):
                anova = {"df": len(grupos) - 1, "F": round(float(F), 4), "p": float(p)}
        except Exception:
            pass

    # --- Parametrico: Tukey HSD ---
    tukey_df = None
    if _TEM_TUKEY and len(grupos) >= 2:
        vals = np.concatenate([v for _, v in grupos])
        labs = np.concatenate([[proto] * len(v) for proto, v in grupos])
        if len(np.unique(labs)) >= 2 and len(vals) >= 3:
            try:
                res = pairwise_tukeyhsd(vals, labs, alpha=alpha)
                tukey_df = pd.DataFrame(res.summary().data[1:], columns=res.summary().data[0])
            except Exception:
                pass

    # --- Nao-parametrico: Kruskal-Wallis (entre todos os grupos) ---
    kruskal = {"H": None, "p": None}
    if len(grupos) >= 2 and all(len(v) >= 1 for _, v in grupos):
        try:
            H, p = stats.kruskal(*[v for _, v in grupos])
            if np.isfinite(H):
                kruskal = {"H": round(float(H), 4), "p": float(p)}
        except Exception:
            pass  # ex.: todos os valores identicos

    # --- Nao-parametrico: Mann-Whitney pareado (two-sided) ---
    mw_linhas = []
    for i in range(len(grupos)):
        for j in range(i + 1, len(grupos)):
            (g1, a), (g2, b) = grupos[i], grupos[j]
            try:
                U, p = stats.mannwhitneyu(a, b, alternative="two-sided")
                mw_linhas.append({"group1": g1, "group2": g2, "U": round(float(U), 2),
                                  "p_value": float(p),
                                  "difere_5pct": "SIM" if p < alpha else "NAO"})
            except Exception:
                mw_linhas.append({"group1": g1, "group2": g2, "U": None,
                                  "p_value": None, "difere_5pct": "-"})
    mannwhitney_df = pd.DataFrame(mw_linhas) if mw_linhas else None

    return resumo, anova, tukey_df, kruskal, mannwhitney_df


def matriz_correlacao(agg, metricas):
    """Correlacao de Pearson (r) e r^2 entre metricas, agrupando todos os protocolos."""
    presentes = [m for m in metricas if m in agg and agg[m].notna().sum() >= 3]
    pares = []
    for i in range(len(presentes)):
        for j in range(i + 1, len(presentes)):
            a, b = presentes[i], presentes[j]
            sub = agg[[a, b]].dropna()
            if len(sub) < 3:
                continue
            r, p = stats.pearsonr(sub[a], sub[b])
            pares.append({"metrica_x": a, "metrica_y": b, "n": len(sub),
                          "pearson_r": round(float(r), 4), "r2": round(float(r) ** 2, 4),
                          "p_value": float(p)})
    return pd.DataFrame(pares)


def fmt_p(p):
    if p is None:
        return "-"
    return "<0,001" if p < 0.001 else f"{p:.4f}".replace(".", ",")


def imprimir_e_salvar(agg, args):
    protocolos = [x.strip() for x in args.protocolos.split(",") if x.strip()]
    metricas = [m.strip() for m in args.metricas.split(",")
                if m.strip() in METRICAS and (m.strip() in agg or m.strip() == "perda_pct")]
    os.makedirs(args.saida, exist_ok=True)

    print("\n" + "=" * 74)
    print(f" ANALISE DoE - Experimento {args.experimento}  "
          f"(janela={args.janela} min, alpha={args.alpha})")
    print("=" * 74)
    for proto in protocolos:
        nrep = int((agg["protocolo"] == proto).sum())
        print(f"  {proto:>9}: {nrep} replicas")
    if not _TEM_TUKEY:
        print("  [aviso] statsmodels ausente -> Tukey HSD sera pulado.")

    testes_linhas = []
    for metrica in metricas:
        rotulo, unidade, sentido = METRICAS[metrica]
        resumo, anova, tukey_df, kruskal, mw_df = analisar_metrica(
            agg, metrica, protocolos, args.alpha)
        if resumo.empty:
            continue

        print("\n" + "-" * 74)
        print(f"# {rotulo}  [{unidade}]  (melhor = {sentido})")
        print("-" * 74)
        print(resumo.to_string(index=False))

        # --- parametrico ---
        if anova["F"] is not None:
            sig = "SIM" if anova["p"] < args.alpha else "NAO"
            print(f"\n  [Parametrico] ANOVA: df={anova['df']}  F={anova['F']}"
                  f"  p={fmt_p(anova['p'])}  -> difere? {sig}")
        if tukey_df is not None:
            print("  Tukey HSD (pares):")
            print(textwrap.indent(tukey_df.to_string(index=False), "    "))
            tukey_df.to_csv(os.path.join(args.saida, f"tukey_{metrica}.csv"), index=False)

        # --- nao-parametrico (metodo do artigo WTF) ---
        if kruskal["H"] is not None:
            sig = "SIM" if kruskal["p"] < args.alpha else "NAO"
            print(f"\n  [Nao-param.] Kruskal-Wallis: H={kruskal['H']}"
                  f"  p={fmt_p(kruskal['p'])}  -> difere? {sig}")
        else:
            print("\n  [Nao-param.] Kruskal-Wallis: n/d (valores constantes ou grupos insuf.)")
        if mw_df is not None:
            print("  Mann-Whitney (pares, two-sided):")
            print(textwrap.indent(mw_df.to_string(index=False), "    "))
            mw_df.to_csv(os.path.join(args.saida, f"mannwhitney_{metrica}.csv"), index=False)

        testes_linhas.append({"metrica": metrica, "rotulo": rotulo, "unidade": unidade,
                              "anova_df": anova["df"], "anova_F": anova["F"],
                              "anova_p": anova["p"],
                              "kruskal_H": kruskal["H"], "kruskal_p": kruskal["p"]})
        resumo.to_csv(os.path.join(args.saida, f"resumo_{metrica}.csv"), index=False)

    pd.DataFrame(testes_linhas).to_csv(os.path.join(args.saida, "testes.csv"), index=False)

    corr = matriz_correlacao(agg, metricas)
    if not corr.empty:
        print("\n" + "-" * 74)
        print("# Correlacao de Pearson entre metricas (todos os protocolos)")
        print("-" * 74)
        print(corr.to_string(index=False))
        corr.to_csv(os.path.join(args.saida, "correlacao.csv"), index=False)

    agg.to_csv(os.path.join(args.saida, "replicas.csv"), index=False)
    print(f"\n[OK] CSVs salvos em: {os.path.abspath(args.saida)}")

    if args.graficos:
        gerar_graficos(agg, metricas, protocolos, args)


def gerar_graficos(agg, metricas, protocolos, args):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("[aviso] matplotlib ausente -> graficos pulados.")
        return

    for metrica in metricas:
        rotulo, unidade, _ = METRICAS[metrica]
        dados = [agg.loc[agg["protocolo"] == p, metrica].dropna().values for p in protocolos]
        if all(len(d) == 0 for d in dados):
            continue
        # boxplot por protocolo
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.boxplot(dados, labels=protocolos, showmeans=True)
        ax.set_title(f"Exp. {args.experimento}: {rotulo}")
        ax.set_ylabel(f"{rotulo} ({unidade})")
        ax.grid(True, axis="y", alpha=0.3)
        fig.tight_layout()
        fig.savefig(os.path.join(args.saida, f"box_{metrica}.png"), dpi=140)
        plt.close(fig)

        # barras media +- IC95
        medias, erros = [], []
        for d in dados:
            m, lo, hi, _ = ic95(d, args.alpha)
            medias.append(m); erros.append((hi - lo) / 2.0 if not np.isnan(hi) else 0)
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.bar(protocolos, medias, yerr=erros, capsize=6, alpha=0.8)
        ax.set_title(f"Exp. {args.experimento}: {rotulo} (media +/- IC95%)")
        ax.set_ylabel(f"{rotulo} ({unidade})")
        ax.grid(True, axis="y", alpha=0.3)
        fig.tight_layout()
        fig.savefig(os.path.join(args.saida, f"barra_{metrica}.png"), dpi=140)
        plt.close(fig)

    print(f"[OK] graficos PNG salvos em: {os.path.abspath(args.saida)}")


def main():
    args = parse_args()
    print(f"=== Analise DoE de protocolos IoT ===  {datetime.now():%Y-%m-%d %H:%M}")
    df = carregar_dados(args)
    agg = montar_replicas(df, args)
    if agg.empty:
        sys.exit("[ERRO] Nenhuma janela valida (tente --janela menor ou --min-amostras menor).")
    imprimir_e_salvar(agg, args)


if __name__ == "__main__":
    main()
