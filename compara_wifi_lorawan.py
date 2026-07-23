#!/usr/bin/env python3
"""Comparacao descritiva: WiFi (real, do artigo) x LoRaWAN (real, do PostgreSQL).

Contexto
--------
O WiFi foi avaliado com HARDWARE REAL no artigo:
  Tejo, J.; Bezerra, T.; Tavares, E. "Avaliacao de Protocolos de Comunicacao
  em Sistemas IoT Medicos com Arquitetura Multi-Cloud" (WTF).
Os dados brutos por mensagem daquele experimento ficavam no InfluxDB, que nao
existe mais nas VMs; portanto os valores de WiFi abaixo sao os AGREGADOS
reportados no artigo (constantes documentadas com a fonte).

O LoRaWAN e REAL e esta vivo no PostgreSQL (no ChirpStack no-uti-01); suas
metricas sao calculadas aqui (media + IC95%), com a mesma janela do DoE.

ATENCAO - latencia NAO e a mesma metrica nos dois:
  * WiFi  = latencia de publicacao MQTT (publish -> ACK do broker, RTT de app)
  * LoRaWAN = time-on-air (airtime de radio, so ida; formula Semtech)
A comparacao e DESCRITIVA e a diferenca de definicao esta anotada na saida.

Uso:
  python3 compara_wifi_lorawan.py --horas 6 --janela 5 --replicas 30 --graficos
"""
import argparse
import os
import sys
from datetime import datetime

try:
    import numpy as np
    import pandas as pd
    from scipy import stats
    import psycopg2
except ImportError as e:  # pragma: no cover
    sys.exit(f"[ERRO] Falta dependencia: {e.name}. Use requirements_analise.txt")

DSN_PADRAO = os.environ.get(
    "PG_DSN", "dbname=iot_medico user=iot password=iotmestrado host=localhost"
)

# ---------------------------------------------------------------------------
# WiFi REAL - valores AGREGADOS reportados no artigo (Tejo et al., WTF),
# em OPERACAO NORMAL (baseline). Injecao de falhas esta fora do escopo.
# ---------------------------------------------------------------------------
WIFI = {
    "fonte": "Tejo, Bezerra, Callou, Tavares - WTF 2026/SBRC 2026 (WiFi real, ESP32+DHT22, multi-cloud)",
    # latencia de publicacao MQTT (publish->ACK), em ms, operacao normal (Fase 1)
    "latencia_ms": {"fase1": 74.8},
    "pdr_pct": {"fase1": 100.0},           # PDR = 1,0 nas janelas observadas
    "disponibilidade_pct": {"fase1": 99.28},
    # nao reportados numericamente / nao medidos no artigo:
    "rssi_dbm": None,      # RSSI "estavel", sem media numerica no texto
    "jitter_ms": None,     # jitter reportado por janela de 10 min, sem escalar unico
    "snr_db": None,        # WiFi nao reporta SNR
    "energia_mah": None,   # energia nao medida no artigo
}

# metrica no banco -> (rotulo, unidade, valor WiFi (fase1) ou None, sentido)
COMPARA = [
    ("latencia_ms", "Latencia",           "ms",  WIFI["latencia_ms"]["fase1"], "menor",
     "WiFi=publish->ACK MQTT ; LoRaWAN=time-on-air (definicoes diferentes)"),
    ("perda_pct",   "Perda de pacotes",   "%",   round(100 - WIFI["pdr_pct"]["fase1"], 4), "menor",
     "WiFi PDR=1,0 -> perda 0% nas janelas observadas"),
    ("pdr",         "PDR (entrega)",      "0-1", WIFI["pdr_pct"]["fase1"] / 100.0, "maior", ""),
    ("jitter_ms",   "Jitter",             "ms",  None, "menor", "WiFi nao reporta escalar unico"),
    ("rssi",        "RSSI",               "dBm", None, "maior", "WiFi: 'estavel', sem media numerica"),
    ("snr",         "SNR",                "dB",  None, "maior", "WiFi nao usa/reporta SNR"),
    ("energia_mah", "Energia por msg",    "mAh", None, "menor", "WiFi: energia nao medida no artigo"),
]

METRICAS_JSONB = ["latencia_ms", "jitter_ms", "pdr", "rssi", "snr", "energia_mah"]


def parse_args():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dsn", default=DSN_PADRAO)
    p.add_argument("--janela", type=int, default=5, help="Janela/amostra em min (default 5)")
    p.add_argument("--replicas", type=int, default=30, help="Nº de janelas LoRaWAN (default 30)")
    p.add_argument("--min-amostras", type=int, default=3)
    p.add_argument("--horas", type=float, default=24.0)
    p.add_argument("--desde", default=None)
    p.add_argument("--ate", default=None)
    p.add_argument("--cloud", default=None)
    p.add_argument("--alpha", type=float, default=0.05)
    p.add_argument("--saida", default="./saida_cmp")
    p.add_argument("--graficos", action="store_true")
    return p.parse_args()


def ic95(x, alpha=0.05):
    x = np.asarray(x, dtype=float); x = x[~np.isnan(x)]
    n = len(x); m = float(np.mean(x)) if n else float("nan")
    if n < 2:
        return m, m, m, n
    se = np.std(x, ddof=1) / np.sqrt(n)
    h = se * stats.t.ppf(1 - alpha / 2.0, n - 1)
    return m, m - h, m + h, n


def lorawan_stats(args):
    """Calcula media + IC95% do LoRaWAN por metrica, usando janelas (replicas)."""
    cols = ", ".join(f"(fields->>'{m}')::float AS {m}" for m in METRICAS_JSONB)
    where = ["protocolo='lorawan'"]
    params = {}
    if args.desde:
        where.append("time >= %(desde)s"); params["desde"] = args.desde
    if args.ate:
        where.append("time <= %(ate)s"); params["ate"] = args.ate
    if not args.desde and not args.ate:
        where.append("time > now() - (%(h)s || ' hours')::interval"); params["h"] = str(args.horas)
    if args.cloud:
        where.append("cloud=%(c)s"); params["c"] = args.cloud
    sql = f"SELECT time, {cols} FROM metricas_iot WHERE {' AND '.join(where)} ORDER BY time"

    with psycopg2.connect(args.dsn) as conn:
        df = pd.read_sql_query(sql, conn, params=params)
    if df.empty:
        sys.exit("[ERRO] Sem dados LoRaWAN no intervalo. Ajuste --horas/--desde.")
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df["janela"] = df["time"].dt.floor(f"{args.janela}min")
    g = df.groupby("janela")
    agg = g[METRICAS_JSONB].mean()
    agg["n"] = g.size()
    agg = agg[agg["n"] >= args.min_amostras].reset_index()
    agg["perda_pct"] = (1.0 - agg["pdr"]) * 100.0
    agg = agg.sort_values("janela").tail(args.replicas).reset_index(drop=True)

    out = {}
    for met in ["latencia_ms", "perda_pct", "pdr", "jitter_ms", "rssi", "snr", "energia_mah"]:
        if met in agg:
            out[met] = ic95(agg[met].values, args.alpha)
    return out, len(agg)


def fmt(v, casas=2):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "n/d"
    return f"{v:.{casas}f}".replace(".", ",")


def main():
    args = parse_args()
    os.makedirs(args.saida, exist_ok=True)
    print(f"=== Comparacao WiFi (artigo) x LoRaWAN (Postgres) === {datetime.now():%Y-%m-%d %H:%M}")
    lw, nrep = lorawan_stats(args)
    print(f"[LoRaWAN] {nrep} janelas de {args.janela} min | [WiFi] {WIFI['fonte']}\n")

    linhas = []
    print("=" * 92)
    print(f"{'Metrica':<20}{'Unid':<6}{'WiFi (real, artigo)':<24}{'LoRaWAN (real, Postgres)':<26}{'Melhor':<8}")
    print("=" * 92)
    for met, rot, uni, wifi_val, sentido, obs in COMPARA:
        if met in lw:
            m, lo, hi, n = lw[met]
            lw_txt = f"{fmt(m,3 if met in ('pdr','energia_mah') else 2)} [{fmt(lo,3 if met in ('pdr','energia_mah') else 2)};{fmt(hi,3 if met in ('pdr','energia_mah') else 2)}]"
        else:
            m = None; lw_txt = "n/d"
        wifi_txt = "n/d" if wifi_val is None else fmt(wifi_val, 3 if met in ("pdr",) else 2)
        # decide melhor (so quando os dois tem numero e sao comparaveis)
        melhor = "-"
        if wifi_val is not None and m is not None and met != "latencia_ms":
            if sentido == "menor":
                melhor = "WiFi" if wifi_val < m else "LoRaWAN"
            else:
                melhor = "WiFi" if wifi_val > m else "LoRaWAN"
        print(f"{rot:<20}{uni:<6}{wifi_txt:<24}{lw_txt:<26}{melhor:<8}")
        if obs:
            print(f"  ^ obs: {obs}")
        linhas.append({"metrica": met, "rotulo": rot, "unidade": uni,
                       "wifi_artigo": wifi_val,
                       "lorawan_media": None if m is None else round(m, 5),
                       "lorawan_ic95_min": None if met not in lw else round(lw[met][1], 5),
                       "lorawan_ic95_max": None if met not in lw else round(lw[met][2], 5),
                       "melhor": melhor, "obs": obs})
    print("=" * 92)

    print("\n# Nota: comparacao restrita a OPERACAO NORMAL (Fase 1). Injecao de"
          " falhas/failover fora do escopo.")
    print(f"  WiFi latencia baseline (publish->ACK) = {WIFI['latencia_ms']['fase1']} ms"
          f"  | PDR=1,0 | disponibilidade {WIFI['disponibilidade_pct']['fase1']}%")
    print("  Metodologia do artigo: janelas de 10 min + Kruskal-Wallis/Mann-Whitney (nao-parametrico).")

    pd.DataFrame(linhas).to_csv(os.path.join(args.saida, "comparacao_wifi_lorawan.csv"), index=False)
    print(f"\n[OK] CSV salvo em {os.path.abspath(args.saida)}")

    if args.graficos:
        gerar_graficos(lw, args)


def gerar_graficos(lw, args):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("[aviso] matplotlib ausente."); return

    # Latencia (com nota de definicoes diferentes)
    if "latencia_ms" in lw:
        m, lo, hi, _ = lw["latencia_ms"]
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.bar(["WiFi\n(publish->ACK)", "LoRaWAN\n(time-on-air)"],
               [WIFI["latencia_ms"]["fase1"], m],
               yerr=[0, (hi - lo) / 2], capsize=6, color=["#4C78A8", "#F58518"])
        ax.set_ylabel("Latencia (ms)")
        ax.set_title("Latencia - definicoes DIFERENTES (comparar com cautela)")
        ax.grid(True, axis="y", alpha=0.3)
        fig.tight_layout(); fig.savefig(os.path.join(args.saida, "cmp_latencia.png"), dpi=140)
        plt.close(fig)

    # Perda de pacotes (%)
    if "perda_pct" in lw:
        m, lo, hi, _ = lw["perda_pct"]
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.bar(["WiFi", "LoRaWAN"], [100 - WIFI["pdr_pct"]["fase1"], m],
               yerr=[0, (hi - lo) / 2], capsize=6, color=["#4C78A8", "#F58518"])
        ax.set_ylabel("Perda de pacotes (%)")
        ax.set_title("Perda de pacotes - operacao normal")
        ax.grid(True, axis="y", alpha=0.3)
        fig.tight_layout(); fig.savefig(os.path.join(args.saida, "cmp_perda.png"), dpi=140)
        plt.close(fig)

    print(f"[OK] graficos em {os.path.abspath(args.saida)}")


if __name__ == "__main__":
    main()
