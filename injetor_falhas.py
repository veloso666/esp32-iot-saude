#!/usr/bin/env python3
"""
Injetor de Falhas - IoT Saude Mestrado
Simula falhas no broker MQTT (Mosquitto) parando/iniciando o servico
com tempos aleatorios baseados em distribuicao exponencial.

Baseado no Algoritmo 6.1 (Falha e Reparo) - Thiago Valentim

Uso: sudo python3 injetor_falhas.py [--tempo-max 34] [--ttf-media 300] [--ttr-media 60]

Parametros:
  --tempo-max   Tempo maximo do experimento em minutos (default: 34)
  --ttf-media   Media do TTF (Time To Failure) em segundos (default: 300 = 5min)
  --ttr-media   Media do TTR (Time To Repair) em segundos (default: 60 = 1min)
  --log         Arquivo de log CSV (default: injecao_falhas.csv)
"""

import subprocess
import time
import random
import math
import csv
import argparse
from datetime import datetime

def gerar_tempo_exponencial(media):
    """Gera tempo aleatorio com distribuicao exponencial."""
    return -media * math.log(1 - random.random())

def executar_comando(cmd):
    """Executa comando do sistema e retorna sucesso."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return result.returncode == 0
    except Exception as e:
        print(f"  [ERRO] {e}")
        return False

def verificar_mosquitto():
    """Verifica se o Mosquitto esta rodando."""
    result = subprocess.run(
        "systemctl is-active mosquitto",
        shell=True, capture_output=True, text=True
    )
    return result.stdout.strip() == "active"

def registrar_evento(writer, evento, detalhes=""):
    """Registra evento no CSV."""
    timestamp = datetime.utcnow().isoformat() + "Z"
    writer.writerow([timestamp, evento, detalhes])
    print(f"  [{timestamp}] {evento} {detalhes}")

def main():
    parser = argparse.ArgumentParser(description="Injetor de Falhas - IoT Saude")
    parser.add_argument("--tempo-max", type=int, default=34, help="Tempo maximo em minutos")
    parser.add_argument("--ttf-media", type=int, default=300, help="Media TTF em segundos")
    parser.add_argument("--ttr-media", type=int, default=60, help="Media TTR em segundos")
    parser.add_argument("--log", type=str, default="injecao_falhas.csv", help="Arquivo CSV de log")
    args = parser.parse_args()

    tempo_max_seg = args.tempo_max * 60

    print("=" * 60)
    print("  INJETOR DE FALHAS - IoT Saude Mestrado")
    print("=" * 60)
    print(f"  Tempo maximo:  {args.tempo_max} min ({tempo_max_seg}s)")
    print(f"  TTF media:     {args.ttf_media}s ({args.ttf_media/60:.1f} min)")
    print(f"  TTR media:     {args.ttr_media}s ({args.ttr_media/60:.1f} min)")
    print(f"  Log:           {args.log}")
    print("=" * 60)

    if not verificar_mosquitto():
        print("[AVISO] Mosquitto nao esta rodando! Iniciando...")
        executar_comando("systemctl start mosquitto")
        time.sleep(2)

    with open(args.log, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["timestamp", "evento", "detalhes"])
        registrar_evento(writer, "INICIO_EXPERIMENTO",
            f"tempo_max={args.tempo_max}min ttf_media={args.ttf_media}s ttr_media={args.ttr_media}s")

        tempo_atual = 0
        ciclo = 0

        while tempo_atual < tempo_max_seg:
            ciclo += 1
            ttf = gerar_tempo_exponencial(args.ttf_media)
            ttf = max(10, min(ttf, tempo_max_seg - tempo_atual))

            print(f"\n--- Ciclo {ciclo} ---")
            print(f"  Sistema OPERANDO. Aguardando TTF={ttf:.0f}s ({ttf/60:.1f}min)...")
            registrar_evento(writer, "OPERANDO", f"ciclo={ciclo} ttf={ttf:.0f}s")
            csvfile.flush()

            time.sleep(ttf)
            tempo_atual += ttf

            if tempo_atual >= tempo_max_seg:
                break

            # Injetar falha: parar Mosquitto
            print(f"  >>> INJETANDO FALHA: parando Mosquitto...")
            executar_comando("systemctl stop mosquitto")
            registrar_evento(writer, "FALHA_INJETADA", f"ciclo={ciclo} mosquitto=stopped")
            csvfile.flush()

            ttr = gerar_tempo_exponencial(args.ttr_media)
            ttr = max(5, min(ttr, tempo_max_seg - tempo_atual))

            print(f"  Sistema em FALHA. Aguardando TTR={ttr:.0f}s ({ttr/60:.1f}min)...")

            time.sleep(ttr)
            tempo_atual += ttr

            # Reparar: iniciar Mosquitto
            print(f"  >>> REPARANDO: iniciando Mosquitto...")
            executar_comando("systemctl start mosquitto")
            registrar_evento(writer, "REPARO", f"ciclo={ciclo} ttr={ttr:.0f}s mosquitto=started")
            csvfile.flush()

            time.sleep(2)

        registrar_evento(writer, "FIM_EXPERIMENTO",
            f"ciclos={ciclo} tempo_total={tempo_atual:.0f}s")

    print(f"\n{'=' * 60}")
    print(f"  EXPERIMENTO FINALIZADO")
    print(f"  Ciclos: {ciclo}")
    print(f"  Tempo total: {tempo_atual:.0f}s ({tempo_atual/60:.1f}min)")
    print(f"  Log salvo em: {args.log}")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    main()
