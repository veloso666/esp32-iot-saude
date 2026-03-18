# Chat Sessao 18/03/2026 - IoT Saude Mestrado

**Continuacao do desenvolvimento - Novas metricas, assets para artigo, IPs estaticos**

---

## Resumo da Sessao

Nesta sessao foram implementadas as melhorias solicitadas pelo coorientador Thiago Valentim para o artigo cientifico, incluindo novas metricas de confiabilidade, scripts de injecao de falhas e monitoramento, diagramas de arquitetura e pseudocodigos em LaTeX.

---

## 1. Novas Metricas no ESP32

### Solicitacao
Adicionar metricas de confiabilidade ao firmware do ESP32:
- Tempo de failover
- Tempo total de recuperacao
- Disponibilidade
- Jitter
- Taxa de sucesso no processamento (por servidor)
- Mensagens duplicadas ou fora de ordem (seq number)

### Implementacao (`esp32-iot-saude.ino`)

**Novas variaveis adicionadas:**

```cpp
// Jitter: variacao absoluta entre latencias consecutivas
unsigned long latencia_anterior      = 0;
unsigned long jitter_atual           = 0;
unsigned long jitter_total           = 0;
unsigned long jitter_max             = 0;
unsigned long jitter_count           = 0;

// Disponibilidade: tempo operando vs tempo total
unsigned long tempo_inicio           = 0;
unsigned long tempo_operando_total   = 0;
unsigned long ultimo_tick_operando   = 0;
bool sistema_operando                = false;

// Tempo de failover e recuperacao
unsigned long inicio_deteccao_falha  = 0;
unsigned long tempo_failover_ms      = 0;
unsigned long inicio_falha_primario  = 0;
unsigned long tempo_recuperacao_ms   = 0;

// Contadores por servidor
unsigned long ok_gcp   = 0;
unsigned long ok_aws   = 0;
unsigned long fail_gcp = 0;
unsigned long fail_aws = 0;

// Sequence number
unsigned long seq_number = 0;
```

**Novos campos no payload (total: 22 campos):**
```
...,seq=10928,jitter=3,disponibilidade=99.85,
tempo_failover=3200,tempo_recuperacao=62000,
ok_gcp=9500,ok_aws=1426,fail_gcp=6,fail_aws=0
```

**Funcoes de disponibilidade:**
- `marcarOperando()` - marca inicio de periodo operante
- `marcarInoperante()` - marca fim de periodo operante, acumula tempo
- `calcularDisponibilidade()` - retorna `(tempo_operando / tempo_total) * 100`

**Calculo do jitter:**
```cpp
jitter_atual = abs(latencia_atual - latencia_anterior);
```

**Tempo de failover**: medido desde `inicio_deteccao_falha` (primeiro MQTT connect fail) ate reconexao bem-sucedida no backup.

**Tempo de recuperacao**: medido desde a falha do primario ate o ESP32 conseguir voltar ao primario.

---

## 2. Script de Injecao de Falhas (`injetor_falhas.py`)

### Justificativa
Baseado no **Algoritmo 6.1 (Falha e Reparo)** do Thiago Valentim (doutorado), simula falhas no broker MQTT de forma programatica para validar a resiliencia do sistema de failover.

### Como funciona
1. Gera tempo aleatorio TTF (Time To Failure) com distribuicao exponencial
2. Aguarda o TTF (sistema operando normalmente)
3. Para o Mosquitto (`systemctl stop mosquitto`) - simula falha
4. Gera tempo aleatorio TTR (Time To Repair) com distribuicao exponencial
5. Aguarda o TTR (sistema em falha)
6. Reinicia o Mosquitto (`systemctl start mosquitto`) - simula reparo
7. Repete ate atingir o tempo maximo do experimento

### Uso
```bash
sudo python3 injetor_falhas.py --tempo-max 34 --ttf-media 300 --ttr-media 60
```

### Parametros
| Parametro | Default | Descricao |
|-----------|---------|-----------|
| `--tempo-max` | 34 min | Duracao total do experimento |
| `--ttf-media` | 300s (5min) | Media da distribuicao exponencial para TTF |
| `--ttr-media` | 60s (1min) | Media da distribuicao exponencial para TTR |
| `--log` | injecao_falhas.csv | Arquivo de log CSV |

### Saida CSV
```
timestamp,evento,detalhes
2026-03-18T10:00:00Z,INICIO_EXPERIMENTO,tempo_max=34min ttf_media=300s ttr_media=60s
2026-03-18T10:05:23Z,OPERANDO,ciclo=1 ttf=323s
2026-03-18T10:05:23Z,FALHA_INJETADA,ciclo=1 mosquitto=stopped
2026-03-18T10:06:15Z,REPARO,ciclo=1 ttr=52s mosquitto=started
...
```

---

## 3. Script de Monitoramento de Eventos (`monitor_eventos.py`)

### Justificativa
Baseado no **Algoritmo 6.2 (Monitoramento do Sistema)** do Thiago Valentim, monitora externamente o estado dos brokers MQTT e registra transicoes de estado (operando <-> falha) com timestamps e duracoes.

### Como funciona
1. A cada intervalo (default 2s), testa conexao TCP na porta 1883 de GCP e AWS
2. Detecta transicoes de estado:
   - operando -> falha: registra evento FALHA
   - falha -> operando: registra evento REPARO com duracao da falha
3. Salva tudo em CSV

### Uso
```bash
python3 monitor_eventos.py --intervalo 2 --log monitor_eventos.csv
```

### Saida CSV
```
timestamp,servidor,evento,duracao_falha_ms,estado_gcp,estado_aws
2026-03-18T10:00:00Z,SISTEMA,INICIO_MONITORAMENTO,0,desconhecido,desconhecido
2026-03-18T10:05:24Z,GCP,FALHA,0,operando,operando
2026-03-18T10:06:16Z,GCP,REPARO,52000,nao_operando,operando
```

---

## 4. Diagrama de Arquitetura

Criado em `artigo/diagrama_arquitetura.md` com 3 diagramas Mermaid:

1. **Diagrama completo** - 4 camadas (Sensores, Comunicacao, Cloud, Analise) com todos os componentes incluindo replicacao, injetor de falhas e monitor de eventos
2. **Diagrama simplificado** - fluxo de dados resumido
3. **Diagrama de sequencia** - mostra o fluxo temporal de uma injecao de falha: falha -> failover -> backup -> reparo -> retorno ao primario

Tambem foi gerada uma **imagem PNG** do diagrama de arquitetura.

---

## 5. Pseudocodigos em LaTeX (`artigo/pseudocodigos.tex`)

Criados 3 algoritmos formatados para o artigo:

### Algoritmo 1: Failover Multi-Cloud com Metricas de Confiabilidade
- Logica completa do ESP32 com failover, calculo de jitter, disponibilidade, tempos de failover/recuperacao

### Algoritmo 2: Injecao de Falhas baseada em Distribuicao Exponencial
- Ciclo de falha/reparo com TTF e TTR exponenciais
- Baseado no Algoritmo 6.1 do Thiago

### Algoritmo 3: Monitoramento de Estado do Sistema
- Maquina de estados (operando/nao_operando/desconhecido)
- Registro de eventos com duracao
- Baseado no Algoritmo 6.2 do Thiago

Para usar no artigo:
```latex
\usepackage{algorithm}
\usepackage{algorithmic}
\input{pseudocodigos.tex}
```

---

## 6. IPs Estaticos

### Problema
Ao parar/ligar as VMs, os IPs mudavam, exigindo atualizacao manual em todos os arquivos e configuracoes.

### Solucao

| Cloud | IP Fixo | Tipo | Como |
|-------|---------|------|------|
| **GCP** | 136.115.185.214 | Static External IP | `gcloud compute addresses create` via Cloud Shell |
| **AWS** | 23.21.181.24 | Elastic IP | `aws ec2 allocate-address` + `associate-address` via CLI |

### Arquivos atualizados com novos IPs
- `esp32-iot-saude.ino` - array de servidores
- `monitor_eventos.py` - lista de servidores
- `artigo/diagrama_arquitetura.md` - diagramas
- `README.md` - documentacao completa

### Configuracoes nas VMs (pendente)
- GCP: atualizar `/etc/mosquitto/conf.d/bridge-aws.conf` com IP da AWS
- AWS: atualizar `/etc/mosquitto/conf.d/bridge-gcp.conf` com IP da GCP

---

## 7. GitHub

Todos os arquivos foram enviados/atualizados no repositorio:
**https://github.com/veloso666/esp32-iot-saude**

### Arquivos enviados nesta sessao:
| Arquivo | Acao |
|---------|------|
| `esp32-iot-saude.ino` | Atualizado (novas metricas + IPs) |
| `README.md` | Atualizado (documentacao completa) |
| `injetor_falhas.py` | Novo |
| `monitor_eventos.py` | Novo |
| `artigo/pseudocodigos.tex` | Novo |
| `artigo/diagrama_arquitetura.md` | Novo |
| `mqtt_to_influx_aws.py` | Atualizado |
| `setup-aws.sh` | Atualizado |
| `sync_influx.py` | Atualizado |
| `pinagem.txt` | Atualizado |
| `dht_scan/dht_scan.ino` | Atualizado |

---

## Proximos Passos

1. **Atualizar bridges nas VMs** - mudar IPs nas configs do Mosquitto (GCP e AWS)
2. **Executar experimento completo** - rodar injetor + monitor + ESP32 por 34 minutos
3. **Coletar dados** - exportar CSVs do injetor, monitor e InfluxDB
4. **Analise estatistica** - Python/Pandas/Matplotlib para gerar graficos
5. **Escrita do artigo** - 14 paginas, prazo sexta-feira
6. **Reuniao com Prof. Eduardo** - apresentar resultados
