"""
Experimento E: comportamento sob condições de rede diferentes.

Aplica `tc netem` na interface de saída do container de experimentos e,
para cada condição, mede:
  - o RTT de GET /api/ping (TCP, mesma lógica do Experimento A);
  - a entrega de leituras por UDP (quantas chegam ao painel).

O netem age só na saída deste container, então um atraso de 50 ms soma
cerca de 50 ms ao RTT (a volta não passa pelo netem). Precisa rodar como
root num container com NET_ADMIN (já configurado no compose.yaml):

    docker compose --profile lab exec experimentos python exp_e_condicoes.py

Ao final, a regra do netem é sempre removida, mesmo se der erro.
"""

import argparse
import asyncio
import os
import shutil
import socket
import subprocess
import sys

import websockets

from comum import (
    UDP_HOST,
    UDP_PORT,
    WS_PAINEL_URL,
    cadastrar,
    coletar_updates,
    imprimir_resumo,
    montar_leitura,
    salvar_csv,
)
from exp_a_rtt import medir_rtt

CONDICOES = [
    ("base", None),
    ("atraso_50ms", "delay 50ms"),
    ("atraso_50ms_jitter_10ms", "delay 50ms 10ms distribution normal"),
    ("perda_5pct", "loss 5%"),
    ("perda_10pct", "loss 10%"),
]


def tc(interface, *argumentos, verificar=True):
    comando = ["tc", "qdisc", *argumentos[:1], "dev", interface, "root", *argumentos[1:]]
    print("  $", " ".join(comando))
    return subprocess.run(comando, check=verificar, capture_output=True, text=True)


def aplicar(interface, netem):
    tc(interface, "del", verificar=False)
    if netem:
        tc(interface, "add", "netem", *netem.split())


async def medir_udp(condicao, n, intervalo):
    device_id, token = cadastrar(f"exp-e-{condicao}")
    async with websockets.connect(WS_PAINEL_URL) as painel:
        await asyncio.sleep(0.3)
        coleta = asyncio.create_task(coletar_updates(painel, [device_id], n, ocioso=3.0))
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            for seq in range(1, n + 1):
                sock.sendto(montar_leitura(device_id, token, seq), (UDP_HOST, UDP_PORT))
                await asyncio.sleep(intervalo)
        chegadas = await coleta
    entregues = len(chegadas)
    return {
        "condicao": condicao,
        "enviadas": n,
        "entregues": entregues,
        "perda_pct": round(100 * (1 - entregues / n), 2),
    }


def main():
    parser = argparse.ArgumentParser(description="Experimento E: RTT e perda sob tc netem.")
    parser.add_argument("--interface", default="eth0")
    parser.add_argument("--n-rtt", type=int, default=50, help="requisições de ping por condição")
    parser.add_argument("--n-udp", type=int, default=200, help="datagramas UDP por condição")
    parser.add_argument("--intervalo-udp", type=float, default=0.01)
    parser.add_argument("--condicoes", help="subconjunto, ex.: base,perda_5pct")
    args = parser.parse_args()

    if os.geteuid() != 0 or shutil.which("tc") is None:
        sys.exit(
            "Este experimento precisa do comando tc e de privilégio de root "
            "(rode dentro do container 'experimentos', que tem NET_ADMIN)."
        )

    condicoes = CONDICOES
    if args.condicoes:
        escolhidas = set(args.condicoes.split(","))
        condicoes = [c for c in CONDICOES if c[0] in escolhidas]

    amostras_rtt, linhas_udp = [], []
    try:
        for nome, netem in condicoes:
            print(f"Condição {nome} ({netem or 'sem netem'})")
            aplicar(args.interface, netem)

            amostras = medir_rtt(args.n_rtt, intervalo=0.05, condicao=nome)
            imprimir_resumo("  RTT", [a["rtt_ms"] for a in amostras if a["rtt_ms"] != ""])
            amostras_rtt.extend({**a, "netem": netem or ""} for a in amostras)

            linha = asyncio.run(medir_udp(nome, args.n_udp, args.intervalo_udp))
            linha["netem"] = netem or ""
            print(f"  UDP entregues={linha['entregues']}/{linha['enviadas']} perda={linha['perda_pct']}%")
            linhas_udp.append(linha)
    finally:
        aplicar(args.interface, None)
        print("Regra do netem removida.")

    salvar_csv("condicoes_rtt.csv", amostras_rtt)
    salvar_csv("condicoes_udp.csv", linhas_udp)


if __name__ == "__main__":
    main()
