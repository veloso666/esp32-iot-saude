#!/usr/bin/env python3
"""
Gera graficos de analise dos resultados do experimento de injecao de falhas.
Mestrado CIn/UFPE - Joao Lucas Veloso
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.dates as mdates
import csv
import os
from datetime import datetime, timedelta

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "artigo")
os.makedirs(OUTPUT_DIR, exist_ok=True)

CSV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "monitor_eventos.csv")

CORES = {
    "operando": "#2E7D32",
    "falha": "#C62828",
    "reparo": "#1565C0",
    "aws": "#F57F17",
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


def filtrar_gcp(eventos):
    falhas = []
    for e in eventos:
        if e["servidor"] == "GCP" and e["evento"] in ("FALHA", "REPARO"):
            falhas.append(e)
    return falhas


def grafico_timeline(eventos):
    """Grafico 1: Timeline do experimento com barras de estado."""
    fig, ax = plt.subplots(figsize=(16, 6))
    fig.patch.set_facecolor("white")

    gcp_events = [e for e in eventos if e["servidor"] == "GCP" and e["evento"] in ("FALHA", "REPARO", "OPERANDO_INICIAL")]
    aws_events = [e for e in eventos if e["servidor"] == "AWS" and e["evento"] in ("FALHA", "REPARO", "OPERANDO_INICIAL")]

    inicio = eventos[0]["timestamp"]
    fim_exp1 = inicio + timedelta(minutes=34)

    # GCP timeline (y=1)
    estado_gcp = "operando"
    ultimo_ts = inicio
    for e in gcp_events:
        if e["timestamp"] > fim_exp1:
            break
        if e["evento"] == "FALHA":
            cor = CORES["operando"]
            ax.barh(1, (e["timestamp"] - ultimo_ts).total_seconds(), left=(ultimo_ts - inicio).total_seconds(),
                    color=cor, height=0.4, alpha=0.7)
            ultimo_ts = e["timestamp"]
            estado_gcp = "falha"
        elif e["evento"] == "REPARO":
            cor = CORES["falha"]
            ax.barh(1, (e["timestamp"] - ultimo_ts).total_seconds(), left=(ultimo_ts - inicio).total_seconds(),
                    color=cor, height=0.4, alpha=0.7)
            ultimo_ts = e["timestamp"]
            estado_gcp = "operando"
    if ultimo_ts < fim_exp1:
        cor = CORES["operando"] if estado_gcp == "operando" else CORES["falha"]
        ax.barh(1, (fim_exp1 - ultimo_ts).total_seconds(), left=(ultimo_ts - inicio).total_seconds(),
                color=cor, height=0.4, alpha=0.7)

    # AWS timeline (y=0)
    ax.barh(0, (fim_exp1 - inicio).total_seconds(), left=0,
            color=CORES["aws"], height=0.4, alpha=0.5)

    # Marcadores de falha
    falha_num = 0
    for e in gcp_events:
        if e["timestamp"] > fim_exp1:
            break
        if e["evento"] == "FALHA":
            falha_num += 1
            x = (e["timestamp"] - inicio).total_seconds()
            ax.axvline(x, color=CORES["falha"], linestyle="--", alpha=0.5, linewidth=1)
            ax.text(x, 1.35, f"F{falha_num}", ha="center", fontsize=9, fontweight="bold", color=CORES["falha"])
        elif e["evento"] == "REPARO":
            x = (e["timestamp"] - inicio).total_seconds()
            ax.axvline(x, color=CORES["reparo"], linestyle=":", alpha=0.5, linewidth=1)

    ax.set_yticks([0, 1])
    ax.set_yticklabels(["AWS\n(Backup)", "GCP\n(Primario)"], fontsize=11, fontweight="bold")
    ax.set_xlabel("Tempo do experimento (segundos)", fontsize=12)
    ax.set_title("Timeline do Experimento - Estado dos Servidores", fontsize=14, fontweight="bold", color=CORES["titulo"], pad=15)
    ax.set_xlim(0, (fim_exp1 - inicio).total_seconds())
    ax.set_ylim(-0.5, 2)
    ax.grid(axis="x", color=CORES["grid"], linestyle="-", alpha=0.5)

    legend = [
        mpatches.Patch(color=CORES["operando"], alpha=0.7, label="GCP Operando"),
        mpatches.Patch(color=CORES["falha"], alpha=0.7, label="GCP em Falha"),
        mpatches.Patch(color=CORES["aws"], alpha=0.5, label="AWS Operando (Backup)"),
    ]
    ax.legend(handles=legend, loc="upper right", fontsize=10, framealpha=0.9)

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "04_timeline_experimento.png")
    fig.savefig(path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"[OK] {path}")
    return path


def grafico_duracao_falhas(eventos):
    """Grafico 2: Duracao de cada falha (barras)."""
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor("white")

    reparos = [e for e in eventos if e["servidor"] == "GCP" and e["evento"] == "REPARO"]

    ciclos = list(range(1, len(reparos) + 1))
    duracoes_s = [r["duracao_ms"] / 1000 for r in reparos]

    bars = ax.bar(ciclos, duracoes_s, color=[CORES["falha"]] * len(ciclos), alpha=0.8, width=0.6, edgecolor="white", linewidth=1.5)

    for bar, dur in zip(bars, duracoes_s):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2,
                f"{dur:.1f}s", ha="center", fontsize=11, fontweight="bold", color=CORES["falha"])

    media = sum(duracoes_s) / len(duracoes_s)
    ax.axhline(media, color=CORES["reparo"], linestyle="--", linewidth=2, alpha=0.7)
    ax.text(len(ciclos) + 0.3, media, f"Media: {media:.1f}s", fontsize=10, color=CORES["reparo"], fontweight="bold", va="center")

    ax.set_xlabel("Ciclo de Falha", fontsize=12)
    ax.set_ylabel("Duracao da Falha (segundos)", fontsize=12)
    ax.set_title("Duracao de Cada Falha Detectada (GCP)", fontsize=14, fontweight="bold", color=CORES["titulo"], pad=15)
    ax.set_xticks(ciclos)
    ax.set_xticklabels([f"Ciclo {c}" for c in ciclos], fontsize=10)
    ax.grid(axis="y", color=CORES["grid"], linestyle="-", alpha=0.5)

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "05_duracao_falhas.png")
    fig.savefig(path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"[OK] {path}")
    return path


def grafico_disponibilidade(eventos):
    """Grafico 3: Disponibilidade ao longo do tempo."""
    fig, ax = plt.subplots(figsize=(14, 6))
    fig.patch.set_facecolor("white")

    gcp_events = [e for e in eventos if e["servidor"] == "GCP" and e["evento"] in ("FALHA", "REPARO", "OPERANDO_INICIAL")]

    inicio = eventos[0]["timestamp"]
    fim_exp1 = inicio + timedelta(minutes=34)

    tempos = []
    disponibilidades = []

    tempo_operando = 0
    tempo_total = 0
    estado = "operando"
    ultimo_ts = inicio

    pontos_check = [inicio + timedelta(seconds=s) for s in range(0, 34 * 60 + 1, 10)]
    idx_evento = 0

    for t in pontos_check:
        while idx_evento < len(gcp_events) and gcp_events[idx_evento]["timestamp"] <= t:
            e = gcp_events[idx_evento]
            dt = (e["timestamp"] - ultimo_ts).total_seconds()
            tempo_total += dt
            if estado == "operando":
                tempo_operando += dt
            ultimo_ts = e["timestamp"]
            if e["evento"] == "FALHA":
                estado = "falha"
            elif e["evento"] == "REPARO":
                estado = "operando"
            idx_evento += 1

        dt = (t - ultimo_ts).total_seconds()
        tempo_total_now = tempo_total + dt
        tempo_operando_now = tempo_operando + (dt if estado == "operando" else 0)

        if tempo_total_now > 0:
            disp = (tempo_operando_now / tempo_total_now) * 100
        else:
            disp = 100

        tempos.append((t - inicio).total_seconds())
        disponibilidades.append(disp)

    ax.plot(tempos, disponibilidades, color=CORES["operando"], linewidth=2.5, label="Disponibilidade GCP")
    ax.fill_between(tempos, disponibilidades, alpha=0.15, color=CORES["operando"])

    ax.axhline(100, color=CORES["aws"], linestyle="--", linewidth=1.5, alpha=0.7, label="AWS (100%)")

    # Marcar falhas
    falha_num = 0
    for e in gcp_events:
        if e["timestamp"] > fim_exp1:
            break
        if e["evento"] == "FALHA":
            falha_num += 1
            x = (e["timestamp"] - inicio).total_seconds()
            ax.axvline(x, color=CORES["falha"], linestyle="--", alpha=0.3, linewidth=1)
            ax.text(x, 102, f"F{falha_num}", ha="center", fontsize=8, color=CORES["falha"], fontweight="bold")

    disp_final = disponibilidades[-1]
    ax.text(tempos[-1] - 50, disp_final - 3, f"{disp_final:.1f}%", fontsize=12, fontweight="bold", color=CORES["operando"])

    ax.set_xlabel("Tempo do experimento (segundos)", fontsize=12)
    ax.set_ylabel("Disponibilidade (%)", fontsize=12)
    ax.set_title("Disponibilidade do GCP ao Longo do Experimento", fontsize=14, fontweight="bold", color=CORES["titulo"], pad=15)
    ax.set_xlim(0, (fim_exp1 - inicio).total_seconds())
    ax.set_ylim(75, 105)
    ax.grid(color=CORES["grid"], linestyle="-", alpha=0.5)
    ax.legend(loc="lower left", fontsize=10, framealpha=0.9)

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "06_disponibilidade.png")
    fig.savefig(path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"[OK] {path}")
    return path


def grafico_resumo(eventos):
    """Grafico 4: Resumo do experimento (pizza + metricas)."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), gridspec_kw={"width_ratios": [1, 1.2]})
    fig.patch.set_facecolor("white")
    fig.suptitle("Resumo do Experimento de Injecao de Falhas", fontsize=14, fontweight="bold", color=CORES["titulo"], y=1.02)

    reparos = [e for e in eventos if e["servidor"] == "GCP" and e["evento"] == "REPARO"]
    tempo_falha_total = sum(r["duracao_ms"] for r in reparos) / 1000
    tempo_total = 34 * 60
    tempo_operando = tempo_total - tempo_falha_total

    # Pizza
    sizes = [tempo_operando, tempo_falha_total]
    labels = [f"Operando\n{tempo_operando:.0f}s ({tempo_operando/60:.1f}min)", f"Em Falha\n{tempo_falha_total:.0f}s ({tempo_falha_total/60:.1f}min)"]
    colors = [CORES["operando"], CORES["falha"]]
    explode = (0, 0.08)

    wedges, texts, autotexts = ax1.pie(sizes, labels=labels, colors=colors, explode=explode,
                                        autopct="%1.1f%%", startangle=90, textprops={"fontsize": 10},
                                        pctdistance=0.6)
    for t in autotexts:
        t.set_fontweight("bold")
        t.set_fontsize(12)
        t.set_color("white")
    ax1.set_title("Distribuicao do Tempo", fontsize=12, fontweight="bold", pad=10)

    # Tabela de metricas
    ax2.axis("off")

    disponibilidade = (tempo_operando / tempo_total) * 100
    duracoes = [r["duracao_ms"] / 1000 for r in reparos]
    media_falha = sum(duracoes) / len(duracoes) if duracoes else 0
    max_falha = max(duracoes) if duracoes else 0
    min_falha = min(duracoes) if duracoes else 0

    metricas = [
        ("Duracao do Experimento", f"{tempo_total}s (34 min)"),
        ("Falhas Injetadas", f"{len(reparos)}"),
        ("Tempo Total em Falha", f"{tempo_falha_total:.1f}s ({tempo_falha_total/60:.1f} min)"),
        ("Tempo Operando", f"{tempo_operando:.1f}s ({tempo_operando/60:.1f} min)"),
        ("Disponibilidade GCP", f"{disponibilidade:.1f}%"),
        ("Disponibilidade AWS", "100%"),
        ("Duracao Media de Falha", f"{media_falha:.1f}s"),
        ("Maior Falha", f"{max_falha:.1f}s ({max_falha/60:.1f} min)"),
        ("Menor Falha", f"{min_falha:.1f}s"),
        ("Delay de Deteccao", "~2s (intervalo TCP)"),
    ]

    table = ax2.table(
        cellText=[[v] for _, v in metricas],
        rowLabels=[k for k, _ in metricas],
        colLabels=["Valor"],
        cellLoc="center",
        rowLoc="right",
        loc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 1.8)

    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_facecolor(CORES["titulo"])
            cell.set_text_props(color="white", fontweight="bold")
        elif col == -1:
            cell.set_facecolor("#E8EAF6")
            cell.set_text_props(fontweight="bold", fontsize=9)
        else:
            cell.set_facecolor("#FAFAFA")

    ax2.set_title("Metricas do Experimento", fontsize=12, fontweight="bold", pad=10)

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "07_resumo_experimento.png")
    fig.savefig(path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"[OK] {path}")
    return path


if __name__ == "__main__":
    print("=" * 50)
    print("  Gerando graficos de analise...")
    print("=" * 50)

    eventos = parse_csv()
    print(f"  {len(eventos)} eventos carregados do CSV")

    grafico_timeline(eventos)
    grafico_duracao_falhas(eventos)
    grafico_disponibilidade(eventos)
    grafico_resumo(eventos)

    print("=" * 50)
    print(f"  Graficos salvos em: {OUTPUT_DIR}")
    print("=" * 50)
