# Experimentos de rede

Scripts da avaliação experimental (Experimentos A a E) e geração dos gráficos.
Todos gravam CSV em `resultados/`; o `graficos.py` lê esses CSVs e gera os PNGs e um
`resumo.md` com as tabelas para o relatório.

| Script | O que mede | Saída |
|--------|------------|-------|
| `exp_a_rtt.py` | RTT de `GET /api/ping` (mín. 30 medições), com e sem conexão nova | `rtt_<condicao>.csv` |
| `exp_b_throughput.py` | Vazão e perda por tamanho de mensagem (100 B a 100 KB), WebSocket e UDP | `throughput.csv` |
| `exp_c_concorrencia.py` | Taxa e atraso com 1, 2 e 5 clientes simultâneos (um processo por cliente) | `concorrencia_<canal>.csv` e `_amostras.csv` |
| `exp_d_tcp_udp.py` | TCP vs UDP com sockets puros, mesma carga; perda e ordem pelo `seq` | `tcp_udp_<condicao>.csv` |
| `exp_e_condicoes.py` | RTT e entrega UDP sob `tc netem` (atraso, jitter, perda) | `condicoes_rtt.csv`, `condicoes_udp.csv` |
| `graficos.py` | Gráficos e tabela-resumo | `exp_*.png`, `resumo.md` |

Os scripts cadastram os próprios dispositivos via `POST /api/dispositivos`, então não
dependem do `.env` nem dos sensores do compose.

## Antes de medir

Suba **só o servidor** e o container de experimentos. Os sensores do compose mandam
leituras a cada 2 s e isso vira carga extra durante a medição (principalmente no
Experimento C).

```bash
docker compose up -d --build servidor
docker compose --profile lab up -d --build experimentos
```

Para a demonstração e o vídeo, aí sim vale subir o painel e os sensores.

## Rodando (dentro do container, recomendado)

Dentro do container o tráfego passa pela rede bridge do Docker, de container para
container, e o `tc netem` funciona. Os endereços já vêm das variáveis do compose.

```bash
docker compose --profile lab exec experimentos python exp_a_rtt.py --n 50 --condicao docker
docker compose --profile lab exec experimentos python exp_a_rtt.py --n 50 --condicao docker_sem_keepalive --nova-conexao
docker compose --profile lab exec experimentos python exp_b_throughput.py
docker compose --profile lab exec experimentos python exp_c_concorrencia.py
docker compose --profile lab exec experimentos python exp_c_concorrencia.py --canal udp
docker compose --profile lab exec experimentos python exp_d_tcp_udp.py
docker compose --profile lab exec experimentos python exp_e_condicoes.py
docker compose --profile lab exec experimentos python graficos.py
```

Como a pasta `experimentos/` é montada no container, os resultados aparecem direto em
`experimentos/resultados/` na sua máquina.

## Rodando no host (sem Docker)

Funciona para A, B, C e D (o E precisa de Linux com root). Com o servidor rodando em
`localhost:8000`:

```bash
pip install -r experimentos/requirements.txt
cd experimentos
python exp_a_rtt.py --n 50 --condicao host
```

Variáveis aceitas: `API_BASE_URL`, `WS_URL`, `WS_PAINEL_URL`, `UDP_HOST`, `UDP_PORT` e
`RESULTADOS_DIR` (pasta de saída).

## Experimento D com o receptor em outro container

No modo padrão, emissor e receptor ficam no mesmo processo (loopback), onde quase nunca
há perda. Para ver o efeito de perda de rede, rode o receptor num segundo container e
aplique o netem no emissor:

```bash
docker compose --profile lab run -d --rm --name exp-receptor experimentos python exp_d_tcp_udp.py --modo receptor
docker compose --profile lab exec experimentos tc qdisc add dev eth0 root netem loss 5%
docker compose --profile lab exec experimentos python exp_d_tcp_udp.py --modo emissor --host exp-receptor --condicao perda_5pct
docker compose --profile lab exec experimentos tc qdisc del dev eth0 root
docker stop exp-receptor
```

## Pontos para a análise

- **Experimento A:** com `--nova-conexao`, cada requisição inclui o 3-way handshake do
  TCP; a diferença para o caso com keep-alive mostra o custo de abrir conexão.
- **Experimento B:** o UDP não fragmenta mensagens na aplicação. Um datagrama IPv4 tem
  no máximo 65.507 bytes de dados, então 100 KB nunca sai do emissor (`Message too long`).
  No macOS o limite padrão é ainda menor (9.216 bytes, `net.inet.udp.maxdgram`), por isso
  10 KB também falha quando o script roda no host. No gráfico isso aparece como
  "não enviado", e não como perda na rede.
- **Experimento C:** `atraso_servidor_ms` usa o `recebido_em` do `update` (horário do
  servidor) menos o `timestamp` do sensor. Como cliente e servidor rodam na mesma
  máquina, os relógios são os mesmos.
- **Experimento D:** a comparação usa a mesma carga (mesmo número de mensagens, tamanho e
  taxa), mas TCP e UDP não são equivalentes: o TCP garante entrega e ordem com
  retransmissão e controle de congestionamento, e o UDP não garante nada.
- **Experimento E:** o netem age só na saída do container de experimentos, então um
  atraso de 50 ms soma cerca de 50 ms ao RTT. Com perda, o TCP retransmite (o RTT sobe,
  mas a requisição chega) e o UDP simplesmente perde a leitura.
