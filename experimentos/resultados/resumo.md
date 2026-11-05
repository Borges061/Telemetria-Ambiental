# Resumo dos experimentos

## Experimento A: RTT (ms)

| condicao | n | media | mediana | desvio | min | max |
|---|---|---|---|---|---|---|
| docker | 50 | 4.319 | 4.704 | 1.098 | 0.718 | 5.663 |
| docker_sem_keepalive | 50 | 6.187 | 6.342 | 1.488 | 0.978 | 8.429 |

## Experimento B: vazão por tamanho

| canal | tamanho_bytes | enviadas | entregues | perda_pct | duracao_envio_s | duracao_total_s | msgs_s | kb_s | erro |
|---|---|---|---|---|---|---|---|---|---|
| ws | 100 | 200 | 200 | 0.0 | 0.3331 | 0.3926 | 509.44 | 49.75 |  |
| ws | 1000 | 200 | 200 | 0.0 | 0.345 | 0.3505 | 570.64 | 557.27 |  |
| ws | 10000 | 200 | 200 | 0.0 | 0.3604 | 0.3688 | 542.33 | 5296.19 |  |
| ws | 100000 | 200 | 200 | 0.0 | 0.3888 | 0.422 | 473.92 | 46281.62 |  |
| udp | 100 | 200 | 200 | 0.0 | 0.038 | 0.3453 | 579.24 | 56.57 |  |
| udp | 1000 | 200 | 200 | 0.0 | 0.0415 | 0.3474 | 575.65 | 562.16 |  |
| udp | 10000 | 200 | 200 | 0.0 | 0.0474 | 0.3528 | 566.95 | 5536.58 |  |
| udp | 100000 | 0 | 0 | 100.0 | 0.0021 | 0.0 | 0.0 | 0.0 | OSError: Message too long |

## Experimento C: concorrência (UDP)

| clientes | canal | enviadas | entregues | perda_pct | duracao_s | msgs_s | taxa_oferecida_msgs_s | atraso_servidor_media_ms | atraso_servidor_mediana_ms | atraso_painel_media_ms | atraso_painel_mediana_ms | atraso_painel_desvio_ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | udp | 100 | 100 | 0.0 | 5.336 | 18.74 | 20.0 | 1.742 | 1.614 | 9.216 | 9.388 | 2.98 |
| 2 | udp | 200 | 200 | 0.0 | 5.391 | 37.1 | 40.0 | 4.387 | 2.168 | 9.206 | 8.637 | 3.224 |
| 5 | udp | 500 | 500 | 0.0 | 5.259 | 95.07 | 100.0 | 6.777 | 6.724 | 9.162 | 8.866 | 4.588 |

## Experimento C: concorrência (WebSocket (TCP))

| clientes | canal | enviadas | entregues | perda_pct | duracao_s | msgs_s | taxa_oferecida_msgs_s | atraso_servidor_media_ms | atraso_servidor_mediana_ms | atraso_painel_media_ms | atraso_painel_mediana_ms | atraso_painel_desvio_ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | ws | 100 | 100 | 0.0 | 5.394 | 18.54 | 20.0 | 1.602 | 1.47 | 8.922 | 8.946 | 2.842 |
| 2 | ws | 200 | 200 | 0.0 | 5.236 | 38.2 | 40.0 | 3.956 | 1.466 | 8.503 | 7.611 | 3.403 |
| 5 | ws | 500 | 500 | 0.0 | 5.215 | 95.88 | 100.0 | 6.593 | 6.697 | 8.929 | 8.776 | 4.783 |

## Experimento D: TCP vs UDP (bridge, média das repetições)

| proto | tamanho_bytes | mbit_s | mbit_s_desvio | perda_pct | fora_ordem |
|---|---|---|---|---|---|
| tcp | 64 | 259.626 | 132.272 | 0.0 | 0.0 |
| tcp | 512 | 813.368 | 76.416 | 0.0 | 0.0 |
| tcp | 1400 | 2141.985 | 682.258 | 0.0 | 0.0 |
| udp | 64 | 5.981 | 0.063 | 0.0 | 0.0 |
| udp | 512 | 47.67 | 0.644 | 0.0 | 0.0 |
| udp | 1400 | 124.537 | 6.121 | 0.0 | 0.0 |

## Experimento D: TCP vs UDP (bridge_perda_5pct, média das repetições)

| proto | tamanho_bytes | mbit_s | mbit_s_desvio | perda_pct | fora_ordem |
|---|---|---|---|---|---|
| tcp | 64 | 146.968 | 195.601 | 0.0 | 0.0 |
| tcp | 512 | 24.338 | 5.28 | 0.0 | 0.0 |
| tcp | 1400 | 27.986 | 4.603 | 0.0 | 0.0 |
| udp | 64 | 5.555 | 0.096 | 4.807 | 0.0 |
| udp | 512 | 44.189 | 0.529 | 4.867 | 0.0 |
| udp | 1400 | 124.265 | 1.389 | 5.013 | 0.0 |

## Experimento D: TCP vs UDP (loopback, média das repetições)

| proto | tamanho_bytes | mbit_s | mbit_s_desvio | perda_pct | fora_ordem |
|---|---|---|---|---|---|
| tcp | 64 | 85.997 | 0.502 | 0.0 | 0.0 |
| tcp | 512 | 626.241 | 7.001 | 0.0 | 0.0 |
| tcp | 1400 | 1512.776 | 4.349 | 0.0 | 0.0 |
| udp | 64 | 57.929 | 1.187 | 0.0 | 0.0 |
| udp | 512 | 467.379 | 3.981 | 0.0 | 0.0 |
| udp | 1400 | 966.244 | 49.708 | 30.033 | 0.0 |

## Experimento E: RTT por condição (ms)

| condicao | n | media | mediana | desvio | min | max |
|---|---|---|---|---|---|---|
| base | 50 | 4.323 | 4.598 | 1.342 | 0.745 | 7.165 |
| atraso_50ms | 50 | 58.441 | 58.175 | 1.842 | 54.281 | 62.496 |
| atraso_50ms_jitter_10ms | 50 | 57.683 | 58.484 | 8.351 | 37.119 | 76.607 |
| perda_5pct | 50 | 16.55 | 4.234 | 49.363 | 1.204 | 213.712 |
| perda_10pct | 50 | 29.098 | 4.623 | 79.092 | 0.813 | 415.779 |

## Experimento E: entrega UDP por condição

| condicao | enviadas | entregues | perda_pct | netem |
|---|---|---|---|---|
| base | 200 | 200 | 0.0 |  |
| atraso_50ms | 200 | 200 | 0.0 | delay 50ms |
| atraso_50ms_jitter_10ms | 200 | 200 | 0.0 | delay 50ms 10ms distribution normal |
| perda_5pct | 200 | 188 | 6.0 | loss 5% |
| perda_10pct | 200 | 180 | 10.0 | loss 10% |
