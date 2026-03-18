#!/usr/bin/env python3
"""
Monitor de Eventos - IoT Saude Mestrado
Monitora o estado dos brokers MQTT (GCP e AWS) e registra
eventos de falha e reparo em CSV.

Baseado no Algoritmo 6.2 (Monitoramento do Sistema) - Thiago Valentim

Uso: python3 monitor_eventos.py [--intervalo 2] [--log monitor_eventos.csv]

Pode rodar no PC local ou em qualquer maquina com acesso aos servidores.
"""

import socket
import time
import csv
import argparse
from datetime import datetime

SERVIDORES = [
    {"nome": "GCP", "host": "136.115.185.214", "porta": 1883},
    {"nome": "AWS", "host": "23.21.181.24", "porta": 1883},
]

def testar_conexao(host, porta, timeout=3):
    """Testa se a porta TCP esta acessivel."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, porta))
        sock.close()
        return result == 0
    except Exception:
        return False

def main():
    parser = argparse.ArgumentParser(description="Monitor de Eventos - IoT Saude")
    parser.add_argument("--intervalo", type=int, default=2, help="Intervalo de checagem em segundos")
    parser.add_argument("--log", type=str, default="monitor_eventos.csv", help="Arquivo CSV de log")
    args = parser.parse_args()

    print("=" * 60)
    print("  MONITOR DE EVENTOS - IoT Saude Mestrado")
    print("=" * 60)
    for srv in SERVIDORES:
        print(f"  {srv['nome']}: {srv['host']}:{srv['porta']}")
    print(f"  Intervalo: {args.intervalo}s")
    print(f"  Log: {args.log}")
    print("=" * 60)

    # Estado de cada servidor
    estado = {}
    inicio_falha = {}
    contadores = {}
    for srv in SERVIDORES:
        nome = srv["nome"]
        estado[nome] = "desconhecido"
        inicio_falha[nome] = None
        contadores[nome] = {"falhas": 0, "reparos": 0, "tempo_falha_total": 0}

    with open(args.log, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "timestamp", "servidor", "evento", "duracao_falha_ms",
            "estado_gcp", "estado_aws"
        ])

        timestamp = datetime.utcnow().isoformat() + "Z"
        writer.writerow([timestamp, "SISTEMA", "INICIO_MONITORAMENTO", 0,
                        "desconhecido", "desconhecido"])
        csvfile.flush()

        print(f"\n[{timestamp}] Monitoramento iniciado. Ctrl+C para parar.\n")

        try:
            while True:
                for srv in SERVIDORES:
                    nome = srv["nome"]
                    conectado = testar_conexao(srv["host"], srv["porta"])
                    timestamp = datetime.utcnow().isoformat() + "Z"

                    if conectado:
                        if estado[nome] != "operando":
                            # Transicao para operando (reparo)
                            duracao = 0
                            if inicio_falha[nome] is not None:
                                duracao = int((time.time() - inicio_falha[nome]) * 1000)
                                contadores[nome]["tempo_falha_total"] += duracao
                                inicio_falha[nome] = None

                            if estado[nome] != "desconhecido":
                                contadores[nome]["reparos"] += 1
                                print(f"  [{timestamp}] {nome}: REPARO (falha durou {duracao}ms)")
                                writer.writerow([
                                    timestamp, nome, "REPARO", duracao,
                                    estado["GCP"], estado["AWS"]
                                ])
                            else:
                                print(f"  [{timestamp}] {nome}: OPERANDO (estado inicial)")
                                writer.writerow([
                                    timestamp, nome, "OPERANDO_INICIAL", 0,
                                    estado["GCP"], estado["AWS"]
                                ])

                            estado[nome] = "operando"
                            csvfile.flush()
                    else:
                        if estado[nome] == "operando" or estado[nome] == "desconhecido":
                            # Transicao para falha
                            estado[nome] = "nao_operando"
                            inicio_falha[nome] = time.time()
                            contadores[nome]["falhas"] += 1

                            print(f"  [{timestamp}] {nome}: FALHA DETECTADA")
                            writer.writerow([
                                timestamp, nome, "FALHA", 0,
                                estado["GCP"], estado["AWS"]
                            ])
                            csvfile.flush()

                # Status periodico a cada 30 verificacoes
                time.sleep(args.intervalo)

        except KeyboardInterrupt:
            timestamp = datetime.utcnow().isoformat() + "Z"
            writer.writerow([timestamp, "SISTEMA", "FIM_MONITORAMENTO", 0,
                            estado["GCP"], estado["AWS"]])
            csvfile.flush()

            print(f"\n\n{'=' * 60}")
            print(f"  MONITORAMENTO FINALIZADO")
            print(f"{'=' * 60}")
            for srv in SERVIDORES:
                nome = srv["nome"]
                c = contadores[nome]
                print(f"  {nome}:")
                print(f"    Falhas detectadas:  {c['falhas']}")
                print(f"    Reparos detectados: {c['reparos']}")
                print(f"    Tempo em falha:     {c['tempo_falha_total']}ms")
            print(f"  Log salvo em: {args.log}")
            print(f"{'=' * 60}")

if __name__ == "__main__":
    main()
