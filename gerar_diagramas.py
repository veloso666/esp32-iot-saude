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
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import matplotlib.image as mpimg
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
    fig, ax = plt.subplots(1, 1, figsize=(20, 14))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    ICON_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "artigo", "icons")

    def img_box(ax, cx, cy, img_file, label, zoom=0.035):
        path = os.path.join(ICON_DIR, img_file)
        if os.path.exists(path):
            img = mpimg.imread(path)
            im = OffsetImage(img, zoom=zoom)
            ab = AnnotationBbox(im, (cx, cy + 0.018), frameon=False, zorder=5)
            ax.add_artist(ab)
        ax.text(cx, cy - 0.032, label, ha="center", va="top",
                fontsize=7.5, fontweight="bold", color="#37474F", linespacing=1.1)

    def box(ax, x, y, w, h, title, sub, bg, border, fs=9):
        r = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.008",
                           facecolor=bg, edgecolor=border, linewidth=1.8)
        ax.add_patch(r)
        ax.text(x + w/2, y + h * 0.62, title, ha="center", va="center",
                fontsize=fs, fontweight="bold", color=border)
        if sub:
            ax.text(x + w/2, y + h * 0.28, sub, ha="center", va="center",
                    fontsize=6.5, color="#78909C")

    def cloud(ax, x, y, w, h, title, sub, bg, border):
        r = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.015",
                           facecolor=bg, edgecolor=border, linewidth=2.8)
        ax.add_patch(r)
        ax.text(x + w/2, y + h - 0.015, title, ha="center", va="top",
                fontsize=12, fontweight="bold", color=border)
        ax.text(x + w/2, y + h - 0.042, sub, ha="center", va="top",
                fontsize=7.5, color=border, alpha=0.7)

    def arr(ax, x1, y1, x2, y2, c="#546E7A", lw=1.5, dash=False):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-|>", color=c, lw=lw,
                                    linestyle="--" if dash else "-"))

    def darr(ax, x1, y1, x2, y2, c="#546E7A", lw=2):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="<|-|>", color=c, lw=lw))

    # ========== TITULO ==========
    ax.text(0.50, 0.98, "Arquitetura do Sistema", ha="center", va="top",
            fontsize=20, fontweight="bold", color="#263238")
    ax.text(0.50, 0.015, "Avaliacao de Desempenho de Protocolos IoT Aplicados no Contexto Medico  |  CIn/UFPE  |  Joao Lucas Veloso",
            ha="center", va="bottom", fontsize=8, color="#9E9E9E")

    B = 0.075; H = 0.055

    # ====================================================================
    # CAMADA ESQUERDA: SENSORES + PROTOCOLOS
    # ====================================================================
    sensor_area = FancyBboxPatch((0.02, 0.50), 0.11, 0.28, boxstyle="round,pad=0.008",
                                  facecolor="#E8F5E9", edgecolor="#43A047", linewidth=1.5, alpha=0.5)
    ax.add_patch(sensor_area)
    ax.text(0.075, 0.765, "SENSORES", ha="center", fontsize=8, fontweight="bold", color="#2E7D32")

    box(ax, 0.033, 0.68, B, H, "ESP32", "DevKit-C V4", "#C8E6C9", "#2E7D32", 8)
    box(ax, 0.033, 0.60, B, H, "DHT22", "Temp/Umidade", "#C8E6C9", "#2E7D32", 8)
    box(ax, 0.033, 0.52, B, H, "Simulado", "FC / SpO2", "#C8E6C9", "#2E7D32", 8)

    proto_area = FancyBboxPatch((0.145, 0.56), 0.09, 0.16, boxstyle="round,pad=0.008",
                                 facecolor="#EDE7F6", edgecolor="#5C6BC0", linewidth=1.2, alpha=0.4)
    ax.add_patch(proto_area)
    ax.text(0.19, 0.71, "PROTOCOLO", ha="center", fontsize=7.5, fontweight="bold", color="#5C6BC0")
    img_box(ax, 0.19, 0.64, "wifi.png", "WiFi / MQTT", zoom=0.12)

    arr(ax, 0.033 + B, 0.71, 0.165, 0.65, "#43A047", lw=1.8)

    # ====================================================================
    # CLOUD GCP (centro-esquerda)
    # ====================================================================
    gx, gy, gw, gh = 0.26, 0.46, 0.28, 0.44
    cloud(ax, gx, gy, gw, gh, "Google Cloud Platform",
          "136.115.185.214 | us-central1", "#E3F2FD", "#1565C0")

    c1 = gx + 0.065; c2 = gx + 0.20
    img_box(ax, c1, 0.82, "mosquitto.png", "Mosquitto\n:1883", zoom=0.15)
    img_box(ax, c2, 0.82, "bridge.png", "Bridge\nMQTT\u2192Influx", zoom=0.10)
    img_box(ax, c1, 0.68, "influxdb.png", "InfluxDB\n:8086", zoom=0.11)
    img_box(ax, c2, 0.68, "grafana.jpg", "Grafana\n:3000", zoom=0.14)
    box(ax, c1 - B/2, 0.50, B, H, "Injetor", "Falhas", "#FFCDD2", "#B71C1C")
    box(ax, c2 - B/2, 0.50, B, H, "Sync", "InfluxDB", "#E8EAF6", "#3F51B5")

    arr(ax, c1 + 0.035, 0.82, c2 - 0.035, 0.82, "#546E7A")
    arr(ax, c1, 0.77, c1, 0.72, "#546E7A")
    arr(ax, c2, 0.77, c2, 0.72, "#546E7A")

    # ====================================================================
    # CLOUD AWS (direita)
    # ====================================================================
    ax2, ay, aw2, ah2 = 0.70, 0.46, 0.28, 0.44
    cloud(ax, ax2, ay, aw2, ah2, "Amazon Web Services",
          "23.21.181.24 | us-east-1", "#FFF8E1", "#F57F17")

    a1 = ax2 + 0.065; a2 = ax2 + 0.20
    img_box(ax, a1, 0.82, "mosquitto.png", "Mosquitto\n:1883", zoom=0.15)
    img_box(ax, a2, 0.82, "bridge.png", "Bridge\nMQTT\u2192Influx", zoom=0.10)
    img_box(ax, a1, 0.68, "influxdb.png", "InfluxDB\n:8086", zoom=0.11)
    img_box(ax, a2, 0.68, "grafana.jpg", "Grafana\n:3000", zoom=0.14)
    box(ax, a1 - B/2, 0.50, B, H, "Sync", "InfluxDB", "#E8EAF6", "#3F51B5")

    arr(ax, a1 + 0.035, 0.82, a2 - 0.035, 0.82, "#546E7A")
    arr(ax, a1, 0.77, a1, 0.72, "#546E7A")
    arr(ax, a2, 0.77, a2, 0.72, "#546E7A")

    # ====================================================================
    # CONEXOES ENTRE CLOUDS
    # ====================================================================
    mx = (gx + gw + ax2) / 2

    darr(ax, gx + gw + 0.01, 0.82, ax2 - 0.01, 0.82, "#FF6F00", lw=2.5)
    ax.text(mx, 0.845, "MQTT Bridge", ha="center", fontsize=8.5, fontweight="bold",
            color="#FF6F00", bbox=dict(boxstyle="round,pad=0.25", facecolor="white",
            edgecolor="#FF6F00", linewidth=1.2))

    darr(ax, gx + gw + 0.01, 0.53, ax2 - 0.01, 0.53, "#3F51B5", lw=1.5)
    ax.text(mx, 0.55, "InfluxDB Sync (5 min)", ha="center", fontsize=7, fontweight="bold",
            color="#3F51B5", bbox=dict(boxstyle="round,pad=0.2", facecolor="white",
            edgecolor="#3F51B5", linewidth=1))

    # ====================================================================
    # WIFI -> CLOUDS
    # ====================================================================
    arr(ax, 0.235, 0.69, gx + 0.01, 0.80, "#1565C0", lw=2.5)
    ax.text(0.245, 0.76, "Primario", ha="center", fontsize=9, fontweight="bold",
            color="#1565C0", rotation=28,
            bbox=dict(boxstyle="round,pad=0.2", facecolor="white", edgecolor="none", alpha=0.9))


    # ====================================================================
    # CAMADA INFERIOR: METRICAS + ANALISE + LEGENDA
    # ====================================================================

    # --- Metricas (embaixo esquerda) ---
    mr = FancyBboxPatch((0.02, 0.04), 0.22, 0.33, boxstyle="round,pad=0.008",
                        facecolor="#FAFAFA", edgecolor="#B0BEC5", linewidth=1, linestyle=":")
    ax.add_patch(mr)
    ax.text(0.13, 0.35, "Metricas Coletadas (22 campos)", ha="center", fontsize=8,
            fontweight="bold", color="#37474F")

    metrics = [
        "Temperatura / Umidade / FC / SpO2",
        "RSSI / Consumo / Latencia / Jitter",
        "PDR / Disponibilidade / Seq#",
        "Tempo Failover / Recuperacao",
        "Pacotes OK/Fail por servidor",
    ]
    for i, m in enumerate(metrics):
        ax.text(0.035, 0.31 - i * 0.052, "\u2022 " + m, fontsize=7.5, color="#546E7A")

    # --- Analise (embaixo centro) ---
    anr = FancyBboxPatch((0.26, 0.04), 0.36, 0.33, boxstyle="round,pad=0.008",
                         facecolor="#F3E5F5", edgecolor="#7B1FA2", linewidth=1.5, alpha=0.4)
    ax.add_patch(anr)
    ax.text(0.44, 0.35, "ANALISE E RESULTADOS", ha="center", fontsize=8.5,
            fontweight="bold", color="#7B1FA2")

    box(ax, 0.28, 0.25, B, H, "Monitor", "Eventos", "#C8E6C9", "#2E7D32")
    box(ax, 0.38, 0.25, B, H, "Export", "CSV", "#F3E5F5", "#7B1FA2")
    box(ax, 0.50, 0.25, B, H, "Python", "Matplotlib", "#F3E5F5", "#7B1FA2")

    arr(ax, 0.28 + B, 0.278, 0.38, 0.278, "#7B1FA2")
    arr(ax, 0.38 + B, 0.278, 0.50, 0.278, "#7B1FA2")

    art = FancyBboxPatch((0.33, 0.06), 0.22, 0.065, boxstyle="round,pad=0.008",
                         facecolor="#E1BEE7", edgecolor="#7B1FA2", linewidth=1.5)
    ax.add_patch(art)
    ax.text(0.44, 0.093, "Dissertacao / Artigo", ha="center", fontsize=9,
            fontweight="bold", color="#4A148C")

    arr(ax, 0.44, 0.25, 0.44, 0.125, "#7B1FA2")

    arr(ax, 0.28 + B/2, 0.25 + H, 0.28 + B/2, gy, "#2E7D32", dash=True)
    ax.text(0.34, gy - 0.01, "TCP check", ha="left", fontsize=6.5,
            color="#2E7D32", fontweight="bold")

    # --- Legenda (embaixo direita) ---
    leg_area = FancyBboxPatch((0.66, 0.06), 0.32, 0.12, boxstyle="round,pad=0.008",
                               facecolor="#FAFAFA", edgecolor="#CFD8DC", linewidth=1)
    ax.add_patch(leg_area)
    ax.text(0.82, 0.165, "Legenda", ha="center", fontsize=8, fontweight="bold", color="#546E7A")

    items = [
        ("#E0F7FA", "#00838F", "MQTT Broker"),
        ("#FFF3E0", "#E65100", "Banco de Dados"),
        ("#FFEBEE", "#C62828", "Visualizacao"),
        ("#E3F2FD", "#1565C0", "Processamento"),
        ("#FFCDD2", "#B71C1C", "Injecao Falhas"),
        ("#C8E6C9", "#2E7D32", "Monitoramento"),
    ]
    for i, (bg, border, label) in enumerate(items):
        lx = 0.68 + (i % 2) * 0.15
        ly = 0.135 - (i // 2) * 0.03
        lr = FancyBboxPatch((lx, ly), 0.012, 0.012, boxstyle="round,pad=0.001",
                            facecolor=bg, edgecolor=border, linewidth=1)
        ax.add_patch(lr)
        ax.text(lx + 0.017, ly + 0.006, label, va="center", fontsize=7, color="#546E7A")

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
