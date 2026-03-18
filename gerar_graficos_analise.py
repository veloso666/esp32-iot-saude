#!/usr/bin/env python3
"""
Gera graficos de analise dos resultados do experimento de injecao de falhas.
Mestrado CIn/UFPE - Joao Lucas Veloso

Uso:
  python gerar_graficos_analise.py                           # usa monitor_eventos.csv
  python gerar_graficos_analise.py monitor_eventos_4h.csv    # usa arquivo especifico
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import csv
import os
import sys
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "artigo")
os.makedirs(OUTPUT_DIR, exist_ok=True)

CSV_FILE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE_DIR, "monitor_eventos.csv")
if not os.path.isabs(CSV_FILE):
    CSV_FILE = os.path.join(BASE_DIR, CSV_FILE)

CORES = {
    "operando": "#2E7D32",
    "falha": "#C62828",
    "reparo": "#1565C0",
    "aws_op": "#F57F17",
    "aws_falha": "#E65100",
    "gcp": "#1976D2",
    "bg": "#FAFAFA",
    "grid": "#E0E0E0",
    "titulo": "#1A237E",
}


def parse_csv():
    eventos = []
    with open(CSV_FILE, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ts = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
            eventos.append({
                "timestamp": ts,
                "servidor": row["servidor"],
                "evento": row["evento"],
                "duracao_ms": int(row["duracao_falha_ms"]),
            })
    return eventos


def calc_duracao_experimento(eventos):
    inicio = eventos[0]["timestamp"]
    fim = eventos[-1]["timestamp"]
    return inicio, fim, (fim - inicio).total_seconds()


def grafico_timeline(eventos):
    """Timeline do experimento com barras de estado para GCP e AWS."""
    inicio, fim, duracao_s = calc_duracao_experimento(eventos)
    duracao_min = duracao_s / 60

    gcp_events = [e for e in eventos if e["servidor"] == "GCP" and e["evento"] in ("FALHA", "REPARO", "OPERANDO_INICIAL")]
    aws_events = [e for e in eventos if e["servidor"] == "AWS" and e["evento"] in ("FALHA", "REPARO", "OPERANDO_INICIAL")]

    fig, ax = plt.subplots(figsize=(18, 6))
    fig.patch.set_facecolor("white")

    def draw_timeline(events, y, cor_op, cor_falha, label):
        estado = "operando"
        ultimo_ts = inicio
        for e in events:
            if e["evento"] == "FALHA":
                ax.barh(y, (e["timestamp"] - ultimo_ts).total_seconds() / 60,
                        left=(ultimo_ts - inicio).total_seconds() / 60,
                        color=cor_op, height=0.4, alpha=0.7)
                ultimo_ts = e["timestamp"]
                estado = "falha"
            elif e["evento"] == "REPARO":
                ax.barh(y, (e["timestamp"] - ultimo_ts).total_seconds() / 60,
                        left=(ultimo_ts - inicio).total_seconds() / 60,
                        color=cor_falha, height=0.4, alpha=0.7)
                ultimo_ts = e["timestamp"]
                estado = "operando"
        cor_final = cor_op if estado == "operando" else cor_falha
        ax.barh(y, (fim - ultimo_ts).total_seconds() / 60,
                left=(ultimo_ts - inicio).total_seconds() / 60,
                color=cor_final, height=0.4, alpha=0.7)

    draw_timeline(gcp_events, 1, CORES["operando"], CORES["falha"], "GCP")
    draw_timeline(aws_events, 0, CORES["aws_op"], CORES["aws_falha"], "AWS")

    falha_num = 0
    for e in gcp_events:
        if e["evento"] == "FALHA":
            falha_num += 1
            x = (e["timestamp"] - inicio).total_seconds() / 60
            ax.axvline(x, color=CORES["falha"], linestyle="--", alpha=0.4, linewidth=0.8)
            ax.text(x, 1.35, f"F{falha_num}", ha="center", fontsize=8, fontweight="bold", color=CORES["falha"])

    aws_falha_num = 0
    for e in aws_events:
        if e["evento"] == "FALHA":
            aws_falha_num += 1
            x = (e["timestamp"] - inicio).total_seconds() / 60
            ax.axvline(x, color=CORES["aws_falha"], linestyle=":", alpha=0.4, linewidth=0.8)

    ax.set_yticks([0, 1])
    ax.set_yticklabels(["AWS\n(Backup)", "GCP\n(Primario)"], fontsize=11, fontweight="bold")
    ax.set_xlabel("Tempo do experimento (minutos)", fontsize=12)
    ax.set_title(f"Timeline do Experimento ({duracao_min:.0f} min) - Estado dos Servidores",
                 fontsize=14, fontweight="bold", color=CORES["titulo"], pad=15)
    ax.set_xlim(0, duracao_min)
    ax.set_ylim(-0.5, 2)
    ax.grid(axis="x", color=CORES["grid"], linestyle="-", alpha=0.5)

    legend = [
        mpatches.Patch(color=CORES["operando"], alpha=0.7, label="GCP Operando"),
        mpatches.Patch(color=CORES["falha"], alpha=0.7, label="GCP em Falha"),
        mpatches.Patch(color=CORES["aws_op"], alpha=0.7, label="AWS Operando"),
        mpatches.Patch(color=CORES["aws_falha"], alpha=0.7, label="AWS em Falha"),
    ]
    ax.legend(handles=legend, loc="upper right", fontsize=10, framealpha=0.9)

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "04_timeline_experimento.png")
    fig.savefig(path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"[OK] {path}")


def grafico_duracao_falhas(eventos):
    """Duracao de cada falha GCP e AWS (barras agrupadas)."""
    reparos_gcp = [e for e in eventos if e["servidor"] == "GCP" and e["evento"] == "REPARO"]
    reparos_aws = [e for e in eventos if e["servidor"] == "AWS" and e["evento"] == "REPARO"]

    fig, axes = plt.subplots(1, 2 if reparos_aws else 1,
                             figsize=(16 if reparos_aws else 10, 6),
                             gridspec_kw={"width_ratios": [2, 1] if reparos_aws else [1]})
    fig.patch.set_facecolor("white")
    fig.suptitle("Duracao de Cada Falha Detectada", fontsize=14, fontweight="bold", color=CORES["titulo"], y=1.02)

    if not reparos_aws:
        axes = [axes]

    ax_gcp = axes[0]
    ciclos = list(range(1, len(reparos_gcp) + 1))
    duracoes_s = [r["duracao_ms"] / 1000 for r in reparos_gcp]
    duracoes_min = [d / 60 for d in duracoes_s]

    bars = ax_gcp.bar(ciclos, duracoes_min, color=CORES["falha"], alpha=0.8, width=0.6,
                      edgecolor="white", linewidth=1.5)
    for bar, dur_s, dur_m in zip(bars, duracoes_s, duracoes_min):
        label = f"{dur_m:.1f}min" if dur_s >= 60 else f"{dur_s:.0f}s"
        ax_gcp.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                    label, ha="center", fontsize=9, fontweight="bold", color=CORES["falha"])

    media = sum(duracoes_min) / len(duracoes_min)
    ax_gcp.axhline(media, color=CORES["reparo"], linestyle="--", linewidth=2, alpha=0.7)
    ax_gcp.text(len(ciclos) + 0.3, media, f"Media: {media:.1f}min", fontsize=10,
                color=CORES["reparo"], fontweight="bold", va="center")

    ax_gcp.set_xlabel("Ciclo de Falha", fontsize=12)
    ax_gcp.set_ylabel("Duracao da Falha (minutos)", fontsize=12)
    ax_gcp.set_title(f"GCP - {len(reparos_gcp)} falhas", fontsize=12, fontweight="bold")
    ax_gcp.set_xticks(ciclos)
    ax_gcp.set_xticklabels([f"F{c}" for c in ciclos], fontsize=9)
    ax_gcp.grid(axis="y", color=CORES["grid"], linestyle="-", alpha=0.5)

    if reparos_aws:
        ax_aws = axes[1]
        ciclos_aws = list(range(1, len(reparos_aws) + 1))
        duracoes_aws_s = [r["duracao_ms"] / 1000 for r in reparos_aws]

        bars_aws = ax_aws.bar(ciclos_aws, duracoes_aws_s, color=CORES["aws_falha"], alpha=0.8,
                              width=0.6, edgecolor="white", linewidth=1.5)
        for bar, dur in zip(bars_aws, duracoes_aws_s):
            ax_aws.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                        f"{dur:.1f}s", ha="center", fontsize=9, fontweight="bold", color=CORES["aws_falha"])

        media_aws = sum(duracoes_aws_s) / len(duracoes_aws_s)
        ax_aws.axhline(media_aws, color=CORES["reparo"], linestyle="--", linewidth=2, alpha=0.7)
        ax_aws.text(len(ciclos_aws) + 0.3, media_aws, f"Media: {media_aws:.1f}s", fontsize=10,
                    color=CORES["reparo"], fontweight="bold", va="center")

        ax_aws.set_xlabel("Ciclo de Falha", fontsize=12)
        ax_aws.set_ylabel("Duracao da Falha (segundos)", fontsize=12)
        ax_aws.set_title(f"AWS - {len(reparos_aws)} falhas", fontsize=12, fontweight="bold")
        ax_aws.set_xticks(ciclos_aws)
        ax_aws.set_xticklabels([f"F{c}" for c in ciclos_aws], fontsize=9)
        ax_aws.grid(axis="y", color=CORES["grid"], linestyle="-", alpha=0.5)

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "05_duracao_falhas.png")
    fig.savefig(path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"[OK] {path}")


def grafico_disponibilidade(eventos):
    """Disponibilidade de GCP e AWS ao longo do tempo."""
    inicio, fim, duracao_s = calc_duracao_experimento(eventos)
    duracao_min = duracao_s / 60

    fig, ax = plt.subplots(figsize=(16, 6))
    fig.patch.set_facecolor("white")

    for servidor, cor, label in [("GCP", CORES["operando"], "Disponibilidade GCP"),
                                  ("AWS", CORES["aws_op"], "Disponibilidade AWS")]:
        srv_events = [e for e in eventos if e["servidor"] == servidor and
                      e["evento"] in ("FALHA", "REPARO", "OPERANDO_INICIAL")]

        intervalo = max(10, int(duracao_s / 500))
        pontos_check = [inicio + timedelta(seconds=s) for s in range(0, int(duracao_s) + 1, intervalo)]

        tempos = []
        disponibilidades = []
        tempo_operando = 0
        tempo_total = 0
        estado = "operando"
        ultimo_ts = inicio
        idx_evento = 0

        for t in pontos_check:
            while idx_evento < len(srv_events) and srv_events[idx_evento]["timestamp"] <= t:
                e = srv_events[idx_evento]
                dt = (e["timestamp"] - ultimo_ts).total_seconds()
                tempo_total += dt
                if estado == "operando":
                    tempo_operando += dt
                ultimo_ts = e["timestamp"]
                if e["evento"] == "FALHA":
                    estado = "falha"
                elif e["evento"] in ("REPARO", "OPERANDO_INICIAL"):
                    estado = "operando"
                idx_evento += 1

            dt = (t - ultimo_ts).total_seconds()
            tt = tempo_total + dt
            to = tempo_operando + (dt if estado == "operando" else 0)
            disp = (to / tt) * 100 if tt > 0 else 100

            tempos.append((t - inicio).total_seconds() / 60)
            disponibilidades.append(disp)

        ax.plot(tempos, disponibilidades, color=cor, linewidth=2.5, label=label)
        ax.fill_between(tempos, disponibilidades, alpha=0.1, color=cor)

        if disponibilidades:
            disp_final = disponibilidades[-1]
            ax.text(tempos[-1] - duracao_min * 0.05, disp_final - 1.5,
                    f"{disp_final:.2f}%", fontsize=11, fontweight="bold", color=cor)

    falha_num = 0
    for e in eventos:
        if e["servidor"] == "GCP" and e["evento"] == "FALHA":
            falha_num += 1
            x = (e["timestamp"] - inicio).total_seconds() / 60
            ax.axvline(x, color=CORES["falha"], linestyle="--", alpha=0.3, linewidth=1)
            ax.text(x, ax.get_ylim()[1] + 0.5, f"F{falha_num}", ha="center", fontsize=7,
                    color=CORES["falha"], fontweight="bold")

    ax.set_xlabel("Tempo do experimento (minutos)", fontsize=12)
    ax.set_ylabel("Disponibilidade (%)", fontsize=12)
    ax.set_title(f"Disponibilidade ao Longo do Experimento ({duracao_min:.0f} min)",
                 fontsize=14, fontweight="bold", color=CORES["titulo"], pad=15)
    ax.set_xlim(0, duracao_min)
    y_min = min(min(d for d in [100]) - 5, 85)
    ax.set_ylim(y_min, 102)
    ax.grid(color=CORES["grid"], linestyle="-", alpha=0.5)
    ax.legend(loc="lower left", fontsize=10, framealpha=0.9)

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "06_disponibilidade.png")
    fig.savefig(path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"[OK] {path}")


def grafico_resumo(eventos):
    """Resumo do experimento (pizza GCP + pizza AWS + tabela de metricas)."""
    inicio, fim, duracao_s = calc_duracao_experimento(eventos)
    duracao_min = duracao_s / 60

    reparos_gcp = [e for e in eventos if e["servidor"] == "GCP" and e["evento"] == "REPARO"]
    reparos_aws = [e for e in eventos if e["servidor"] == "AWS" and e["evento"] == "REPARO"]

    falha_gcp_s = sum(r["duracao_ms"] for r in reparos_gcp) / 1000
    falha_aws_s = sum(r["duracao_ms"] for r in reparos_aws) / 1000
    op_gcp_s = duracao_s - falha_gcp_s
    op_aws_s = duracao_s - falha_aws_s

    disp_gcp = (op_gcp_s / duracao_s) * 100
    disp_aws = (op_aws_s / duracao_s) * 100

    dur_gcp = [r["duracao_ms"] / 1000 for r in reparos_gcp]
    dur_aws = [r["duracao_ms"] / 1000 for r in reparos_aws]

    has_aws = len(reparos_aws) > 0
    ncols = 3 if has_aws else 2
    ratios = [1, 1, 1.4] if has_aws else [1, 1.3]

    fig, axes = plt.subplots(1, ncols, figsize=(20 if has_aws else 14, 8),
                             gridspec_kw={"width_ratios": ratios})
    fig.patch.set_facecolor("white")
    fig.suptitle(f"Resumo do Experimento de Injecao de Falhas ({duracao_min:.0f} min)",
                 fontsize=14, fontweight="bold", color=CORES["titulo"], y=1.02)

    def draw_pie(ax, op_s, falha_s, label, cor_op, cor_falha):
        sizes = [op_s, falha_s]
        labels = [f"Operando\n{op_s/60:.1f}min", f"Em Falha\n{falha_s/60:.1f}min"]
        colors = [cor_op, cor_falha]
        wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors, explode=(0, 0.08),
                                           autopct="%1.1f%%", startangle=90, textprops={"fontsize": 10},
                                           pctdistance=0.6)
        for t in autotexts:
            t.set_fontweight("bold")
            t.set_fontsize(12)
            t.set_color("white")
        ax.set_title(f"{label}", fontsize=12, fontweight="bold", pad=10)

    draw_pie(axes[0], op_gcp_s, falha_gcp_s, "GCP (Primario)", CORES["operando"], CORES["falha"])
    if has_aws:
        draw_pie(axes[1], op_aws_s, falha_aws_s, "AWS (Backup)", CORES["aws_op"], CORES["aws_falha"])

    ax_tab = axes[-1]
    ax_tab.axis("off")

    media_gcp = sum(dur_gcp) / len(dur_gcp) if dur_gcp else 0
    max_gcp = max(dur_gcp) if dur_gcp else 0
    min_gcp = min(dur_gcp) if dur_gcp else 0

    def fmt_dur(s):
        if s >= 60:
            return f"{s:.0f}s ({s/60:.1f} min)"
        return f"{s:.1f}s"

    metricas = [
        ("Duracao Total", f"{duracao_s:.0f}s ({duracao_min:.0f} min)"),
        ("", ""),
        ("--- GCP (Primario) ---", ""),
        ("Falhas GCP", f"{len(reparos_gcp)}"),
        ("Tempo em Falha GCP", fmt_dur(falha_gcp_s)),
        ("Disponibilidade GCP", f"{disp_gcp:.2f}%"),
        ("Duracao Media Falha", fmt_dur(media_gcp)),
        ("Maior Falha GCP", fmt_dur(max_gcp)),
        ("Menor Falha GCP", fmt_dur(min_gcp)),
    ]

    if has_aws:
        media_aws = sum(dur_aws) / len(dur_aws) if dur_aws else 0
        max_aws = max(dur_aws) if dur_aws else 0
        min_aws = min(dur_aws) if dur_aws else 0
        metricas += [
            ("", ""),
            ("--- AWS (Backup) ---", ""),
            ("Falhas AWS", f"{len(reparos_aws)}"),
            ("Tempo em Falha AWS", fmt_dur(falha_aws_s)),
            ("Disponibilidade AWS", f"{disp_aws:.2f}%"),
            ("Duracao Media Falha", fmt_dur(media_aws)),
        ]

    metricas = [(k, v) for k, v in metricas if k or v]

    table = ax_tab.table(
        cellText=[[v] for _, v in metricas],
        rowLabels=[k for k, _ in metricas],
        colLabels=["Valor"],
        cellLoc="center",
        rowLoc="right",
        loc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 1.6)

    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_facecolor(CORES["titulo"])
            cell.set_text_props(color="white", fontweight="bold")
        elif col == -1:
            text = cell.get_text().get_text()
            if text.startswith("---"):
                cell.set_facecolor("#C5CAE9")
                cell.set_text_props(fontweight="bold", fontsize=9)
            else:
                cell.set_facecolor("#E8EAF6")
                cell.set_text_props(fontweight="bold", fontsize=9)
        else:
            cell.set_facecolor("#FAFAFA")

    ax_tab.set_title("Metricas do Experimento", fontsize=12, fontweight="bold", pad=10)

    fig.subplots_adjust(left=0.05, right=0.98, top=0.90, bottom=0.05, wspace=0.3)
    path = os.path.join(OUTPUT_DIR, "07_resumo_experimento.png")
    fig.savefig(path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"[OK] {path}")


if __name__ == "__main__":
    print("=" * 50)
    print("  Gerando graficos de analise...")
    print(f"  CSV: {CSV_FILE}")
    print("=" * 50)

    eventos = parse_csv()
    print(f"  {len(eventos)} eventos carregados")

    inicio, fim, dur = calc_duracao_experimento(eventos)
    print(f"  Periodo: {inicio.strftime('%H:%M')} -> {fim.strftime('%H:%M')} ({dur/60:.0f} min)")

    n_falhas_gcp = sum(1 for e in eventos if e["servidor"] == "GCP" and e["evento"] == "FALHA")
    n_falhas_aws = sum(1 for e in eventos if e["servidor"] == "AWS" and e["evento"] == "FALHA")
    print(f"  Falhas GCP: {n_falhas_gcp} | Falhas AWS: {n_falhas_aws}")

    grafico_timeline(eventos)
    grafico_duracao_falhas(eventos)
    grafico_disponibilidade(eventos)
    grafico_resumo(eventos)

    print("=" * 50)
    print(f"  Graficos salvos em: {OUTPUT_DIR}")
    print("=" * 50)
