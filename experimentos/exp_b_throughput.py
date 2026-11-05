"""
Experimento B: vazão (throughput) com mensagens de tamanhos diferentes.

Para cada canal (WebSocket/TCP e UDP) e cada tamanho de mensagem, envia N
leituras o mais rápido possível, completadas com `padding`, e conta quantas
chegaram ao painel como `update`. A vazão é calculada sobre as mensagens
efetivamente processadas pelo servidor, do primeiro envio ao último update.

Uso:
    python exp_b_throughput.py
    python exp_b_throughput.py --tamanhos 100,1000,10000,100000 --n 200
"""

import argparse
import asyncio
import socket
import time

import websockets

from comum import (
    UDP_HOST,
    UDP_PORT,
    WS_PAINEL_URL,
    WS_URL,
    cadastrar,
    coletar_updates,
    montar_leitura,
    salvar_csv,
)


async def enviar_ws(device_id, token, n, tamanho):
    """Envia N leituras pelo /ws/sensor. Devolve (enviadas, erro)."""
    async with websockets.connect(WS_URL, max_size=None) as ws:
        for seq in range(1, n + 1):
            await ws.send(montar_leitura(device_id, token, seq, tamanho).decode("utf-8"))
    return n, ""


def enviar_udp(device_id, token, n, tamanho):
    """Envia N datagramas para a porta UDP. Devolve (enviadas, erro)."""
    enviadas = 0
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        for seq in range(1, n + 1):
            try:
                sock.sendto(montar_leitura(device_id, token, seq, tamanho), (UDP_HOST, UDP_PORT))
                enviadas += 1
            except OSError as exc:
                # Ex.: EMSGSIZE quando o datagrama passa do limite do sistema.
                return enviadas, f"{type(exc).__name__}: {exc.strerror or exc}"
    return enviadas, ""


async def rodar(canal, tamanho, n):
    device_id, token = cadastrar(f"exp-b-{canal}-{tamanho}")

    async with websockets.connect(WS_PAINEL_URL) as painel:
        await asyncio.sleep(0.2)
        coleta = asyncio.create_task(coletar_updates(painel, [device_id], n))

        inicio = time.perf_counter()
        if canal == "ws":
            enviadas, erro = await enviar_ws(device_id, token, n, tamanho)
        else:
            enviadas, erro = await asyncio.to_thread(enviar_udp, device_id, token, n, tamanho)
        fim_envio = time.perf_counter()

        chegadas = await coleta

    entregues = len(chegadas)
    duracao = (chegadas[-1][0] - inicio) if chegadas else 0.0

    return {
        "canal": canal,
        "tamanho_bytes": tamanho,
        "enviadas": enviadas,
        "entregues": entregues,
        "perda_pct": round(100 * (1 - entregues / enviadas), 2) if enviadas else 100.0,
        "duracao_envio_s": round(fim_envio - inicio, 4),
        "duracao_total_s": round(duracao, 4),
        "msgs_s": round(entregues / duracao, 2) if duracao else 0.0,
        "kb_s": round(entregues * tamanho / 1024 / duracao, 2) if duracao else 0.0,
        "erro": erro,
    }


async def main_async(args):
    linhas = []
    for canal in args.canais:
        for tamanho in args.tamanhos:
            print(f"{canal.upper()} {tamanho} B: enviando {args.n} mensagens...")
            linha = await rodar(canal, tamanho, args.n)
            print(
                f"  entregues={linha['entregues']}/{linha['enviadas']} "
                f"perda={linha['perda_pct']}% vazão={linha['kb_s']} KB/s "
                f"({linha['msgs_s']} msg/s) {linha['erro']}"
            )
            linhas.append(linha)
            await asyncio.sleep(1)
    salvar_csv("throughput.csv", linhas)


def main():
    parser = argparse.ArgumentParser(description="Experimento B: vazão por tamanho de mensagem.")
    parser.add_argument("--tamanhos", default="100,1000,10000,100000",
                        help="tamanhos em bytes, separados por vírgula")
    parser.add_argument("--n", type=int, default=200, help="mensagens por combinação")
    parser.add_argument("--canais", default="ws,udp", help="ws, udp ou ambos")
    args = parser.parse_args()

    args.tamanhos = [int(t) for t in args.tamanhos.split(",")]
    args.canais = [c.strip() for c in args.canais.split(",")]
    if any(c not in ("ws", "udp") for c in args.canais):
        parser.error("--canais aceita apenas ws e udp")

    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
