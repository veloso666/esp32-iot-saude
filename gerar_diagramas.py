#!/usr/bin/env python3
"""
Gerador de Diagramas para Artigo - IoT Saude Mestrado
CIn/UFPE - Joao Lucas Veloso

Gera 3 imagens em alta resolucao (300 DPI) para o artigo:
1. Arquitetura Multi-Cloud com Failover e Replicacao
2. Injecao de Falhas (Algoritmo 6.1)
3. Monitoramento de Eventos (Algoritmo 6.2)
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import os

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "artigo")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Cores padrao (inspiradas no diagrama original)
CORES = {
    "sensor":      "#2E7D32",  # verde escuro
    "sensor_bg":   "#E8F5E9",  # verde claro
    "protocolo":   "#4527A0",  # roxo escuro
    "protocolo_bg":"#EDE7F6",  # roxo claro
    "mqtt":        "#00838F",  # teal
    "mqtt_bg":     "#E0F7FA",  # teal claro
    "db":          "#E65100",  # laranja
    "db_bg":       "#FFF3E0",  # laranja claro
    "visual":      "#C62828",  # vermelho
    "visual_bg":   "#FFEBEE",  # vermelho claro
    "bridge":      "#1565C0",  # azul
    "bridge_bg":   "#E3F2FD",  # azul claro
    "cloud_gcp":   "#E3F2FD",  # azul claro
    "cloud_aws":   "#FFF8E1",  # amarelo claro
    "injetor":     "#B71C1C",  # vermelho escuro
    "injetor_bg":  "#FFCDD2",  # vermelho claro
    "monitor":     "#1B5E20",  # verde escuro
    "monitor_bg":  "#C8E6C9",  # verde claro
    "analise_bg":  "#F3E5F5",  # lilas claro
    "fundo":       "#FAFAFA",  # quase branco
    "titulo":      "#1A237E",  # azul escuro
    "texto":       "#212121",  # quase preto
    "seta":        "#424242",  # cinza escuro
    "replicacao":  "#FF6F00",  # amber
    "failover":    "#D32F2F",  # vermelho
}


def caixa(ax, x, y, w, h, titulo, subtitulo, cor_fundo, cor_borda, fontsize=8):
    """Desenha uma caixa com titulo e subtitulo."""
    rect = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02",
                          facecolor=cor_fundo, edgecolor=cor_borda, linewidth=1.5)
    ax.add_patch(rect)
    ax.text(x + w/2, y + h*0.62, titulo, ha="center", va="center",
            fontsize=fontsize, fontweight="bold", color=cor_borda)
    if subtitulo:
        ax.text(x + w/2, y + h*0.3, subtitulo, ha="center", va="center",
                fontsize=fontsize - 1.5, color="#616161")


def area(ax, x, y, w, h, titulo, cor_fundo, cor_borda, fontsize=9):
    """Desenha uma area com borda tracejada e titulo no topo."""
    rect = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.03",
                          facecolor=cor_fundo, edgecolor=cor_borda,
                          linewidth=1.5, linestyle="--")
    ax.add_patch(rect)
    ax.text(x + w/2, y + h - 0.02, titulo, ha="center", va="top",
            fontsize=fontsize, fontweight="bold", color=cor_borda)


def seta(ax, x1, y1, x2, y2, cor="#424242", estilo="-", largura=1.2, label="", tracejada=False):
    """Desenha seta entre dois pontos."""
    ls = "--" if tracejada else "-"
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=cor, lw=largura, linestyle=ls))
    if label:
        mx, my = (x1+x2)/2, (y1+y2)/2
        ax.text(mx, my + 0.015, label, ha="center", va="bottom",
                fontsize=6.5, color=cor, fontstyle="italic")


def seta_dupla(ax, x1, y1, x2, y2, cor="#424242", largura=1.5, label=""):
    """Desenha seta bidirecional."""
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="<|-|>", color=cor, lw=largura))
    if label:
        mx, my = (x1+x2)/2, (y1+y2)/2
        ax.text(mx, my + 0.02, label, ha="center", va="bottom",
                fontsize=7, color=cor, fontweight="bold")


# ============================================================
# DIAGRAMA 1: ARQUITETURA MULTI-CLOUD
# ============================================================
def gerar_arquitetura():
    fig, ax = plt.subplots(1, 1, figsize=(18, 13))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    # Titulo
    ax.text(0.5, 0.98, "ARQUITETURA DO SISTEMA", ha="center", va="top",
            fontsize=18, fontweight="bold", color=CORES["titulo"])
    ax.text(0.5, 0.955, "Avaliacao de Desempenho de Protocolos IoT para Monitoramento de Saude",
            ha="center", va="top", fontsize=10, color="#616161")

    # Medidas padrao
    BW = 0.105   # largura caixa (menor)
    BH = 0.07    # altura caixa (menor)
    GAP = 0.01   # espaco entre caixas

    # =========================================
    # === GCP (topo esquerda) ===
    # =========================================
    gcp_x = 0.02; gcp_y = 0.44; gcp_w = 0.47; gcp_h = 0.46
    area(ax, gcp_x, gcp_y, gcp_w, gcp_h, "",
         CORES["cloud_gcp"], CORES["bridge"], fontsize=10)
    ax.text(gcp_x + gcp_w/2, gcp_y + gcp_h - 0.03, "GOOGLE CLOUD PLATFORM",
            ha="center", va="center", fontsize=12, fontweight="bold", color=CORES["bridge"])
    ax.text(gcp_x + gcp_w/2, gcp_y + gcp_h - 0.06, "136.115.185.214 | us-central1-a",
            ha="center", fontsize=8, color="#1565C0")

    # Linha 1 GCP: Mosquitto -> Bridge -> InfluxDB
    r1y = 0.74
    gcp_c1x = 0.05
    gcp_c2x = gcp_c1x + BW + GAP
    gcp_c3x = gcp_c2x + BW + GAP

    caixa(ax, gcp_c1x, r1y, BW, BH, "Mosquitto", "Porta 1883",
          CORES["mqtt_bg"], CORES["mqtt"], fontsize=8)
    caixa(ax, gcp_c2x, r1y, BW, BH, "Python Bridge", "MQTT to InfluxDB",
          CORES["bridge_bg"], CORES["bridge"], fontsize=8)
    caixa(ax, gcp_c3x, r1y, BW, BH, "InfluxDB", "Porta 8086",
          CORES["db_bg"], CORES["db"], fontsize=8)

    seta(ax, gcp_c1x + BW, r1y + BH/2, gcp_c2x, r1y + BH/2, CORES["seta"])
    seta(ax, gcp_c2x + BW, r1y + BH/2, gcp_c3x, r1y + BH/2, CORES["seta"])

    # Linha 2 GCP: Injetor | (vazio) | Grafana
    r2y = 0.64
    caixa(ax, gcp_c1x, r2y, BW, BH, "Injetor de\nFalhas", "stop/start",
          CORES["injetor_bg"], CORES["injetor"], fontsize=8)
    caixa(ax, gcp_c3x, r2y, BW, BH, "Grafana", "Porta 3000",
          CORES["visual_bg"], CORES["visual"], fontsize=8)

    seta(ax, gcp_c1x + BW/2, r2y + BH, gcp_c1x + BW/2, r1y, CORES["injetor"], tracejada=True)
    seta(ax, gcp_c3x + BW/2, r1y, gcp_c3x + BW/2, r2y + BH, CORES["seta"])

    # Linha 3 GCP: Sync
    r3y = 0.48
    caixa(ax, gcp_c1x, r3y, BW, BH, "InfluxDB Sync", "sync_influx.py",
          "#E8EAF6", "#3F51B5", fontsize=8)

    # =========================================
    # === AWS (topo direita) ===
    # =========================================
    aws_x = 0.51; aws_y = 0.44; aws_w = 0.47; aws_h = 0.46
    area(ax, aws_x, aws_y, aws_w, aws_h, "",
         CORES["cloud_aws"], "#F57F17", fontsize=10)
    ax.text(aws_x + aws_w/2, aws_y + aws_h - 0.03, "AMAZON WEB SERVICES",
            ha="center", va="center", fontsize=12, fontweight="bold", color="#F57F17")
    ax.text(aws_x + aws_w/2, aws_y + aws_h - 0.06, "23.21.181.24 | us-east-1",
            ha="center", fontsize=8, color="#F57F17")

    # Linha 1 AWS: Mosquitto -> Bridge -> InfluxDB
    aws_c1x = 0.54
    aws_c2x = aws_c1x + BW + GAP
    aws_c3x = aws_c2x + BW + GAP

    caixa(ax, aws_c1x, r1y, BW, BH, "Mosquitto", "Porta 1883",
          CORES["mqtt_bg"], CORES["mqtt"], fontsize=8)
    caixa(ax, aws_c2x, r1y, BW, BH, "Python Bridge", "MQTT to InfluxDB",
          CORES["bridge_bg"], CORES["bridge"], fontsize=8)
    caixa(ax, aws_c3x, r1y, BW, BH, "InfluxDB", "Porta 8086",
          CORES["db_bg"], CORES["db"], fontsize=8)

    seta(ax, aws_c1x + BW, r1y + BH/2, aws_c2x, r1y + BH/2, CORES["seta"])
    seta(ax, aws_c2x + BW, r1y + BH/2, aws_c3x, r1y + BH/2, CORES["seta"])

    # Linha 2 AWS: Grafana (alinhado)
    caixa(ax, aws_c3x, r2y, BW, BH, "Grafana", "Porta 3000",
          CORES["visual_bg"], CORES["visual"], fontsize=8)
    seta(ax, aws_c3x + BW/2, r1y, aws_c3x + BW/2, r2y + BH, CORES["seta"])

    # Linha 3 AWS: Sync (alinhado)
    caixa(ax, aws_c3x, r3y, BW, BH, "InfluxDB Sync", "sync_influx.py",
          "#E8EAF6", "#3F51B5", fontsize=8)

    # =========================================
    # === Conexoes entre clouds ===
    # =========================================
    bridge_y = r1y + BH + 0.02
    seta_dupla(ax, gcp_c1x + BW, bridge_y, aws_c1x, bridge_y, CORES["replicacao"], largura=2)
    ax.text(0.50, bridge_y + 0.012, "MQTT Bridge (Replicacao Bidirecional)",
            ha="center", fontsize=9, fontweight="bold", color=CORES["replicacao"],
            bbox=dict(boxstyle="round,pad=0.2", facecolor="white", edgecolor="none", alpha=0.9))

    sync_y = r3y + BH/2
    seta_dupla(ax, gcp_c1x + BW, sync_y, aws_c3x, sync_y, "#3F51B5", largura=1.5)
    ax.text(0.50, sync_y + 0.012, "InfluxDB Sync (a cada 5 min)",
            ha="center", fontsize=8, fontweight="bold", color="#3F51B5",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="white", edgecolor="none", alpha=0.9))

    # =========================================
    # === CAMADA DE SENSORES (embaixo esquerda) ===
    # =========================================
    bot_h = 0.36
    area(ax, 0.02, 0.02, 0.28, bot_h, "CAMADA DE SENSORES",
         CORES["sensor_bg"], CORES["sensor"], fontsize=10)

    caixa(ax, 0.04, 0.25, BW, BH, "ESP32", "DevKit-C V4",
          "#C8E6C9", CORES["sensor"], fontsize=8)
    caixa(ax, 0.04 + BW + GAP, 0.25, BW, BH, "DHT22", "Temp / Umidade",
          "#C8E6C9", CORES["sensor"], fontsize=8)
    caixa(ax, 0.04, 0.15, BW, BH, "Simulado", "FC | SpO2",
          "#C8E6C9", CORES["sensor"], fontsize=8)

    mx = 0.04 + BW + GAP + BW/2
    rect = FancyBboxPatch((0.04 + BW + GAP, 0.06), BW, 0.14, boxstyle="round,pad=0.01",
                          facecolor="#E8F5E9", edgecolor=CORES["sensor"], linewidth=1, linestyle=":")
    ax.add_patch(rect)
    ax.text(mx, 0.175, "Metricas:", ha="center", fontsize=7, fontweight="bold", color=CORES["sensor"])
    ax.text(mx, 0.15, "Latencia | PDR | RSSI", ha="center", fontsize=6.5, color="#616161")
    ax.text(mx, 0.125, "Jitter | Disponibilidade", ha="center", fontsize=6.5, color="#616161")
    ax.text(mx, 0.10, "Consumo | Seq#", ha="center", fontsize=6.5, color="#616161")
    ax.text(mx, 0.075, "Failover | Recuperacao", ha="center", fontsize=6.5, color="#616161")

    # === PROTOCOLOS (embaixo centro-esquerda) ===
    area(ax, 0.32, 0.02, 0.13, bot_h, "PROTOCOLOS",
         CORES["protocolo_bg"], CORES["protocolo"], fontsize=10)

    caixa(ax, 0.335, 0.25, 0.10, BH, "WiFi", "802.11 b/g/n",
          "#D1C4E9", CORES["protocolo"], fontsize=8)
    caixa(ax, 0.335, 0.15, 0.10, BH, "LoRaWAN", "(Futuro)",
          "#E0E0E0", "#9E9E9E", fontsize=8)

    # === CAMADA DE ANALISE (embaixo direita) ===
    area(ax, 0.47, 0.02, 0.51, bot_h, "ANALISE E RESULTADOS",
         CORES["analise_bg"], "#7B1FA2", fontsize=10)

    an_c1x = 0.49
    an_c2x = an_c1x + BW + GAP
    an_c3x = an_c2x + BW + GAP

    caixa(ax, an_c1x, 0.25, BW, BH, "Monitor de\nEventos", "monitor_eventos.py",
          CORES["monitor_bg"], CORES["monitor"], fontsize=8)
    caixa(ax, an_c2x, 0.25, BW, BH, "Export CSV", "Google Drive",
          "#F3E5F5", "#7B1FA2", fontsize=8)
    caixa(ax, an_c3x, 0.25, BW, BH, "Python", "Pandas / Matplotlib",
          "#F3E5F5", "#7B1FA2", fontsize=8)

    caixa(ax, an_c2x, 0.06, 2*BW + GAP, 0.12, "Dissertacao / Artigo",
          "Analise Estatistica dos Resultados",
          "#F3E5F5", "#7B1FA2", fontsize=9)

    seta(ax, an_c2x + BW, 0.285, an_c3x, 0.285, "#7B1FA2")
    seta(ax, an_c3x + BW/2, 0.25, an_c3x + BW/2, 0.18, "#7B1FA2")

    # =========================================
    # === Setas entre camadas ===
    # =========================================
    seta(ax, 0.04 + BW, 0.285, 0.335, 0.285, CORES["seta"], largura=1.5)

    # Primario (Protocolo -> GCP)
    seta(ax, 0.385, 0.38, gcp_c1x + BW/2, r1y, CORES["mqtt"], largura=2)
    ax.text(0.20, 0.58, "Primario", ha="center", fontsize=10,
            fontweight="bold", color=CORES["mqtt"], rotation=60,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="none", alpha=0.9))

    # Failover (Protocolo -> AWS)
    seta(ax, 0.435, 0.38, aws_c1x + BW/2, r1y, CORES["failover"], tracejada=True, largura=2)
    ax.text(0.55, 0.58, "Failover", ha="center", fontsize=10,
            fontweight="bold", color=CORES["failover"], rotation=-55,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="none", alpha=0.9))

    # Monitor -> Clouds
    seta(ax, an_c1x + BW/2, 0.32, an_c1x + BW/2, 0.44, CORES["monitor"], tracejada=True)
    ax.text(an_c1x + BW + 0.01, 0.39, "TCP check", ha="left", fontsize=7.5,
            color=CORES["monitor"], fontweight="bold")

    # === LEGENDA (embaixo esquerda, dentro da area de sensores) ===
    legend_items = [
        mpatches.Patch(facecolor="#C8E6C9", edgecolor=CORES["sensor"], label="Sensores"),
        mpatches.Patch(facecolor="#D1C4E9", edgecolor=CORES["protocolo"], label="Protocolos"),
        mpatches.Patch(facecolor=CORES["mqtt_bg"], edgecolor=CORES["mqtt"], label="Broker MQTT"),
        mpatches.Patch(facecolor=CORES["db_bg"], edgecolor=CORES["db"], label="Banco de Dados"),
        mpatches.Patch(facecolor=CORES["visual_bg"], edgecolor=CORES["visual"], label="Visualizacao"),
        mpatches.Patch(facecolor=CORES["bridge_bg"], edgecolor=CORES["bridge"], label="Processamento"),
        mpatches.Patch(facecolor=CORES["injetor_bg"], edgecolor=CORES["injetor"], label="Injecao de Falhas"),
        mpatches.Patch(facecolor=CORES["monitor_bg"], edgecolor=CORES["monitor"], label="Monitoramento"),
    ]
    ax.legend(handles=legend_items, loc="lower center", fontsize=7,
              title="LEGENDA", title_fontsize=8, framealpha=0.95,
              bbox_to_anchor=(0.50, -0.04), ncol=4)

    # Rodape
    ax.text(0.5, -0.08, "Mestrado em Ciencia da Computacao - CIn/UFPE\n"
            "Joao Lucas Veloso | Orientador: Prof. Eduardo Tavares | Coorientador: Thiago Valentim",
            ha="center", fontsize=8, color="#9E9E9E")

    path = os.path.join(OUTPUT_DIR, "01_arquitetura_multicloud.png")
    fig.savefig(path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"[OK] {path}")
    return path


# ============================================================
# DIAGRAMA 2: INJECAO DE FALHAS
# ============================================================
def gerar_injecao_falhas():
    fig, ax = plt.subplots(1, 1, figsize=(16, 11))
    ax.set_xlim(0, 1)
    ax.set_ylim(-0.02, 1.02)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    BW = 0.10; BH = 0.07; GAP = 0.01

    ax.text(0.5, 1.00, "SISTEMA DE INJECAO DE FALHAS", ha="center", va="top",
            fontsize=16, fontweight="bold", color=CORES["titulo"])
    ax.text(0.5, 0.96, "Baseado no Algoritmo 6.1 - Falha e Reparo (Distribuicao Exponencial)",
            ha="center", va="top", fontsize=10, color="#616161")

    # === INJETOR (esquerda) ===
    top_y = 0.50; top_h = 0.40
    area(ax, 0.02, top_y, 0.28, top_h, "INJETOR DE FALHAS",
         CORES["injetor_bg"], CORES["injetor"], fontsize=10)
    ax.text(0.16, top_y + top_h - 0.05, "injetor_falhas.py", ha="center", fontsize=8,
            color=CORES["injetor"], fontstyle="italic")

    steps = [
        ("1. TTF = exp(media)", "Gerar tempo para falha"),
        ("2. Aguardar TTF", "Sistema operando"),
        ("3. systemctl stop", "Interromper Mosquitto"),
        ("4. TTR = exp(media)", "Gerar tempo de reparo"),
        ("5. Aguardar TTR", "Sistema em falha"),
        ("6. systemctl start", "Restaurar Mosquitto"),
    ]
    for i, (step, desc) in enumerate(steps):
        y = top_y + top_h - 0.10 - i * 0.045
        ax.text(0.04, y, step, fontsize=7.5, fontweight="bold", color=CORES["injetor"])
        ax.text(0.18, y, desc, fontsize=7, color="#616161")

    # === SISTEMA ALVO (centro) ===
    area(ax, 0.33, top_y, 0.34, top_h, "SISTEMA ALVO (GCP)",
         CORES["cloud_gcp"], CORES["bridge"], fontsize=10)

    srv_y1 = top_y + top_h - 0.14
    srv_y2 = srv_y1 - 0.14
    caixa(ax, 0.36, srv_y1, 0.28, BH, "Mosquitto", "MQTT Broker - Porta 1883",
          CORES["mqtt_bg"], CORES["mqtt"], fontsize=8)

    caixa(ax, 0.36, srv_y2, 0.13, BH, "InfluxDB", "Porta 8086",
          CORES["db_bg"], CORES["db"], fontsize=8)
    caixa(ax, 0.50, srv_y2, 0.13, BH, "Grafana", "Porta 3000",
          CORES["visual_bg"], CORES["visual"], fontsize=8)

    seta(ax, 0.50, srv_y1, 0.50, srv_y2 + BH, CORES["seta"])
    seta(ax, 0.30, srv_y1 + BH/2, 0.36, srv_y1 + BH/2, CORES["injetor"], largura=2)
    ax.text(0.33, srv_y1 + BH/2 + 0.015, "stop/start", ha="center", fontsize=7,
            color=CORES["injetor"], fontweight="bold")

    # === RESPOSTA (direita) ===
    area(ax, 0.70, top_y, 0.28, top_h, "RESPOSTA DO SISTEMA",
         "#E8F5E9", CORES["sensor"], fontsize=10)

    caixa(ax, 0.73, srv_y1, 0.22, BH, "ESP32", "Detecta falha (3 tentativas)",
          "#C8E6C9", CORES["sensor"], fontsize=8)
    caixa(ax, 0.73, srv_y2, 0.22, BH, "AWS (Backup)", "Failover automatico",
          CORES["cloud_aws"], "#F57F17", fontsize=8)

    seta(ax, 0.84, srv_y1, 0.84, srv_y2 + BH, CORES["failover"])
    ax.text(0.86, (srv_y1 + srv_y2 + BH) / 2, "failover", ha="left", fontsize=7,
            color=CORES["failover"], fontweight="bold")

    seta(ax, 0.64, srv_y1 + BH/2, 0.73, srv_y1 + BH/2, CORES["seta"], tracejada=True)
    ax.text(0.685, srv_y1 + BH/2 + 0.015, "falha", ha="center", fontsize=7, color=CORES["seta"])

    # === TIMELINE (embaixo) ===
    area(ax, 0.02, 0.04, 0.96, 0.43, "LINHA DO TEMPO DO EXPERIMENTO",
         "#FAFAFA", CORES["titulo"], fontsize=10)

    y_line = 0.26
    ax.plot([0.06, 0.94], [y_line, y_line], color=CORES["seta"], linewidth=2)

    events = [
        (0.08, "t=0", "Inicio", CORES["sensor"]),
        (0.20, "TTF", "Operando\n(normal)", CORES["sensor"]),
        (0.35, "Falha", "stop\nMosquitto", CORES["injetor"]),
        (0.44, "", "ESP32 detecta\n(3 falhas)", CORES["failover"]),
        (0.53, "", "Failover\npara AWS", "#F57F17"),
        (0.64, "TTR", "Em falha\n(aguardando)", CORES["injetor"]),
        (0.75, "Reparo", "start\nMosquitto", CORES["sensor"]),
        (0.84, "", "ESP32 retorna\nao GCP", CORES["mqtt"]),
        (0.94, "t=T_max", "Fim", CORES["titulo"]),
    ]

    for x, label_top, label_bot, cor in events:
        ax.plot(x, y_line, "o", color=cor, markersize=7, zorder=5)
        ax.text(x, y_line + 0.035, label_top, ha="center", fontsize=7,
                fontweight="bold", color=cor)
        ax.text(x, y_line - 0.035, label_bot, ha="center", va="top",
                fontsize=6.5, color=cor)

    # Barras de estado
    ax.fill_between([0.08, 0.35], 0.34, 0.36, color=CORES["sensor"], alpha=0.3)
    ax.text(0.215, 0.35, "OPERANDO", ha="center", fontsize=7, color=CORES["sensor"], fontweight="bold")

    ax.fill_between([0.35, 0.75], 0.34, 0.36, color=CORES["injetor"], alpha=0.3)
    ax.text(0.55, 0.35, "FALHA INJETADA", ha="center", fontsize=7, color=CORES["injetor"], fontweight="bold")

    ax.fill_between([0.75, 0.94], 0.34, 0.36, color=CORES["sensor"], alpha=0.3)
    ax.text(0.845, 0.35, "OPERANDO", ha="center", fontsize=7, color=CORES["sensor"], fontweight="bold")

    # Parametros
    params = "Parametros: T_max = 34 min  |  TTF ~ Exp(media = 5 min)  |  TTR ~ Exp(media = 1 min)"
    ax.text(0.5, 0.08, params, ha="center", fontsize=8.5, color="#616161",
            bbox=dict(boxstyle="round,pad=0.4", facecolor="#F5F5F5", edgecolor="#BDBDBD"))

    ax.text(0.5, 0.01, "Mestrado em Ciencia da Computacao - CIn/UFPE - Joao Lucas Veloso",
            ha="center", fontsize=7, color="#9E9E9E")

    path = os.path.join(OUTPUT_DIR, "02_injecao_falhas.png")
    fig.savefig(path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"[OK] {path}")
    return path


# ============================================================
# DIAGRAMA 3: MONITORAMENTO DE EVENTOS
# ============================================================
def gerar_monitoramento():
    fig, ax = plt.subplots(1, 1, figsize=(16, 11))
    ax.set_xlim(0, 1)
    ax.set_ylim(-0.02, 1.02)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    BW = 0.10; BH = 0.07

    ax.text(0.5, 1.00, "SISTEMA DE MONITORAMENTO DE EVENTOS", ha="center", va="top",
            fontsize=16, fontweight="bold", color=CORES["titulo"])
    ax.text(0.5, 0.96, "Baseado no Algoritmo 6.2 - Monitoramento do Sistema",
            ha="center", va="top", fontsize=10, color="#616161")

    # === MONITOR (esquerda) ===
    top_y = 0.50; top_h = 0.40
    area(ax, 0.02, top_y, 0.28, top_h, "MONITOR DE EVENTOS",
         CORES["monitor_bg"], CORES["monitor"], fontsize=10)
    ax.text(0.16, top_y + top_h - 0.05, "monitor_eventos.py", ha="center", fontsize=8,
            color=CORES["monitor"], fontstyle="italic")

    steps = [
        ("1.", "Conectar TCP porta 1883"),
        ("2.", "Se conectou E estado != operando:"),
        ("",   "   estadoSistema = operando"),
        ("",   "   Registrar REPARO no log"),
        ("3.", "Se nao conectou E estado == operando:"),
        ("",   "   estadoSistema = nao_operando"),
        ("",   "   Registrar FALHA no log"),
        ("4.", "Aguardar intervalo (2s)"),
        ("5.", "Repetir para cada servidor"),
    ]
    for i, (num, desc) in enumerate(steps):
        y = top_y + top_h - 0.10 - i * 0.032
        if num:
            ax.text(0.04, y, num, fontsize=7.5, fontweight="bold", color=CORES["monitor"])
        ax.text(0.065, y, desc, fontsize=7,
                fontweight="bold" if num else "normal",
                color=CORES["monitor"] if num else "#616161")

    # === SERVIDORES (centro) ===
    area(ax, 0.33, top_y, 0.34, top_h, "SERVIDORES MONITORADOS",
         CORES["cloud_gcp"], CORES["bridge"], fontsize=10)

    srv_y1 = top_y + top_h - 0.14
    srv_y2 = srv_y1 - 0.14
    caixa(ax, 0.37, srv_y1, 0.26, BH, "GCP - Mosquitto", "136.115.185.214 : 1883",
          CORES["mqtt_bg"], CORES["mqtt"], fontsize=8)
    caixa(ax, 0.37, srv_y2, 0.26, BH, "AWS - Mosquitto", "23.21.181.24 : 1883",
          CORES["mqtt_bg"], CORES["mqtt"], fontsize=8)

    seta(ax, 0.30, srv_y1 + BH/2, 0.37, srv_y1 + BH/2, CORES["monitor"], tracejada=True)
    ax.text(0.335, srv_y1 + BH/2 + 0.015, "TCP check", ha="center", fontsize=7,
            color=CORES["monitor"], fontweight="bold")
    seta(ax, 0.30, srv_y2 + BH/2, 0.37, srv_y2 + BH/2, CORES["monitor"], tracejada=True)
    ax.text(0.335, srv_y2 + BH/2 + 0.015, "TCP check", ha="center", fontsize=7,
            color=CORES["monitor"], fontweight="bold")

    # === LOG CSV (direita) ===
    area(ax, 0.70, top_y, 0.28, top_h, "REGISTRO DE EVENTOS",
         "#FFF3E0", CORES["db"], fontsize=10)

    caixa(ax, 0.73, srv_y1, 0.22, 0.06, "monitor_eventos.csv", "",
          CORES["db_bg"], CORES["db"], fontsize=8)

    csv_lines = [
        ("timestamp,servidor,evento,duracao", "#616161"),
        ("13:05:24, GCP, FALHA, 0", CORES["injetor"]),
        ("13:05:26, GCP, ESP32->AWS, 0", "#F57F17"),
        ("13:06:16, GCP, REPARO, 52000ms", CORES["sensor"]),
        ("13:06:18, GCP, ESP32->GCP, 0", CORES["mqtt"]),
    ]
    for i, (line, cor) in enumerate(csv_lines):
        y = srv_y1 - 0.03 - i * 0.025
        ax.text(0.735, y, line, fontsize=6.5, fontfamily="monospace", color=cor)

    seta(ax, 0.63, srv_y1 + BH/2, 0.73, srv_y1 + BH/2, CORES["db"])
    ax.text(0.68, srv_y1 + BH/2 + 0.015, "log", ha="center", fontsize=7,
            color=CORES["db"], fontweight="bold")

    # === MAQUINA DE ESTADOS (embaixo) ===
    area(ax, 0.02, 0.02, 0.96, 0.43, "MAQUINA DE ESTADOS DO MONITOR",
         "#FAFAFA", CORES["titulo"], fontsize=10)

    # Estado: Operando
    circle1 = plt.Circle((0.25, 0.26), 0.065, facecolor="#C8E6C9",
                         edgecolor=CORES["sensor"], linewidth=2.5)
    ax.add_patch(circle1)
    ax.text(0.25, 0.26, "OPERANDO", ha="center", va="center",
            fontsize=9, fontweight="bold", color=CORES["sensor"])

    # Estado: Nao Operando
    circle2 = plt.Circle((0.65, 0.26), 0.065, facecolor=CORES["injetor_bg"],
                         edgecolor=CORES["injetor"], linewidth=2.5)
    ax.add_patch(circle2)
    ax.text(0.65, 0.26, "NAO\nOPERANDO", ha="center", va="center",
            fontsize=8, fontweight="bold", color=CORES["injetor"])

    # Estado: Inicio
    circle3 = plt.Circle((0.45, 0.10), 0.04, facecolor="#E0E0E0",
                         edgecolor="#757575", linewidth=1.5)
    ax.add_patch(circle3)
    ax.text(0.45, 0.10, "INICIO", ha="center", va="center",
            fontsize=7, fontweight="bold", color="#757575")

    # Transicao: Operando -> Nao Operando
    seta(ax, 0.32, 0.30, 0.58, 0.30, CORES["injetor"], largura=2)
    ax.text(0.45, 0.33, "conexao falhou -> registrar FALHA", ha="center", fontsize=7.5,
            color=CORES["injetor"], fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="white", edgecolor="none", alpha=0.8))

    # Transicao: Nao Operando -> Operando
    seta(ax, 0.58, 0.22, 0.32, 0.22, CORES["sensor"], largura=2)
    ax.text(0.45, 0.18, "conexao OK -> registrar REPARO", ha="center", fontsize=7.5,
            color=CORES["sensor"], fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="white", edgecolor="none", alpha=0.8))

    # Inicio -> Operando
    seta(ax, 0.45, 0.14, 0.28, 0.20, "#757575", tracejada=True)

    # Info box
    ax.text(0.87, 0.12, "Intervalo: 2s\nProtocolo: TCP\nPorta: 1883\nServidores: 2",
            fontsize=8, color="#616161", va="center",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#F5F5F5", edgecolor="#BDBDBD"))

    ax.text(0.5, -0.01, "Mestrado em Ciencia da Computacao - CIn/UFPE - Joao Lucas Veloso",
            ha="center", fontsize=7, color="#9E9E9E")

    path = os.path.join(OUTPUT_DIR, "03_monitoramento_eventos.png")
    fig.savefig(path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"[OK] {path}")
    return path


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print("=" * 50)
    print("  Gerando diagramas para o artigo...")
    print("=" * 50)

    gerar_arquitetura()
    gerar_injecao_falhas()
    gerar_monitoramento()

    print("=" * 50)
    print(f"  Diagramas salvos em: {OUTPUT_DIR}")
    print("=" * 50)
