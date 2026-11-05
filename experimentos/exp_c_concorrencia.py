"""
Experimento C: múltiplos clientes simultâneos.

Para cada quantidade de clientes (1, 2 e 5 por padrão), cadastra um
dispositivo por cliente e sobe cada cliente como um processo separado
(subprocess), todos enviando leituras ao mesmo tempo. Um painel conectado
ao /ws/painel recebe os updates e mede:
  - atraso sensor -> servidor: recebido_em - timestamp;
  - atraso sensor -> painel: chegada no painel - timestamp;
  - taxa total de mensagens entregues ao painel.

Uso:
    python exp_c_concorrencia.py
    python exp_c_concorrencia.py --clientes 1,2,5 --mensagens 100 --intervalo 0.05
"""

import argparse
import asyncio
import socket
import subprocess
import sys
import time

import websockets

from comum import (
    UDP_HOST,
    UDP_PORT,
    WS_PAINEL_URL,
    WS_URL,
    cadastrar,
    coletar_updates,
    diferenca_ms,
    imprimir_resumo,
    montar_leitura,
    resumo,
    salvar_csv,
)


async def cliente_ws(device_id, token, mensagens, intervalo):
    async with websockets.connect(WS_URL) as ws:
        for seq in range(1, mensagens + 1):
            await ws.send(montar_leitura(device_id, token, seq).decode("utf-8"))
            await asyncio.sleep(intervalo)


def cliente_udp(device_id, token, mensagens, intervalo):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        for seq in range(1, mensagens + 1):
            sock.sendto(montar_leitura(device_id, token, seq), (UDP_HOST, UDP_PORT))
            time.sleep(intervalo)


async def rodar(qtd_clientes, args):
    dispositivos = [cadastrar(f"exp-c-{qtd_clientes}-{i}") for i in range(qtd_clientes)]
    esperado = qtd_clientes * args.mensagens

    async with websockets.connect(WS_PAINEL_URL) as painel:
        await asyncio.sleep(0.2)
        coleta = asyncio.create_task(
            coletar_updates(painel, [d for d, _ in dispositivos], esperado, ocioso=5.0)
        )

        processos = [
            subprocess.Popen([
                sys.executable, __file__, "--cliente",
                "--device-id", device_id, "--token", token,
                "--mensagens", str(args.mensagens),
                "--intervalo", str(args.intervalo),
                "--canal", args.canal,
            ])
            for device_id, token in dispositivos
        ]

        chegadas = await coleta
        for processo in processos:
            processo.wait()

    amostras = []
    for _, chegada_utc, mensagem in chegadas:
        amostras.append({
            "clientes": qtd_clientes,
            "device_id": mensagem["device_id"],
            "id": mensagem.get("id"),
            "atraso_servidor_ms": round(diferenca_ms(mensagem["recebido_em"], mensagem["timestamp"]), 3),
            "atraso_painel_ms": round(diferenca_ms(chegada_utc.isoformat(), mensagem["timestamp"]), 3),
        })

    # Taxa medida entre o primeiro e o último update recebido no painel.
    duracao = chegadas[-1][0] - chegadas[0][0] if len(chegadas) > 1 else 0.0
    atraso_srv = resumo([a["atraso_servidor_ms"] for a in amostras])
    atraso_painel = resumo([a["atraso_painel_ms"] for a in amostras])

    linha = {
        "clientes": qtd_clientes,
        "canal": args.canal,
        "enviadas": esperado,
        "entregues": len(chegadas),
        "perda_pct": round(100 * (1 - len(chegadas) / esperado), 2),
        "duracao_s": round(duracao, 3),
        "msgs_s": round(len(chegadas) / duracao, 2) if duracao else 0.0,
        "taxa_oferecida_msgs_s": round(qtd_clientes / args.intervalo, 2),
        "atraso_servidor_media_ms": round(atraso_srv.get("media", 0), 3),
        "atraso_servidor_mediana_ms": round(atraso_srv.get("mediana", 0), 3),
        "atraso_painel_media_ms": round(atraso_painel.get("media", 0), 3),
        "atraso_painel_mediana_ms": round(atraso_painel.get("mediana", 0), 3),
        "atraso_painel_desvio_ms": round(atraso_painel.get("desvio", 0), 3),
    }
    return linha, amostras


async def main_async(args):
    linhas, todas_amostras = [], []
    for qtd in args.clientes:
        print(f"{qtd} cliente(s) {args.canal.upper()}, {args.mensagens} mensagens cada...")
        linha, amostras = await rodar(qtd, args)
        print(
            f"  entregues={linha['entregues']}/{linha['enviadas']} "
            f"taxa={linha['msgs_s']} msg/s (oferecida {linha['taxa_oferecida_msgs_s']})"
        )
        imprimir_resumo("  atraso sensor->servidor", [a["atraso_servidor_ms"] for a in amostras])
        imprimir_resumo("  atraso sensor->painel", [a["atraso_painel_ms"] for a in amostras])
        linhas.append(linha)
        todas_amostras.extend(amostras)
        await asyncio.sleep(1)

    salvar_csv(f"concorrencia_{args.canal}.csv", linhas)
    salvar_csv(f"concorrencia_{args.canal}_amostras.csv", todas_amostras)


def main():
    parser = argparse.ArgumentParser(description="Experimento C: clientes simultâneos.")
    parser.add_argument("--clientes", default="1,2,5", help="quantidades de clientes, separadas por vírgula")
    parser.add_argument("--mensagens", type=int, default=100, help="mensagens por cliente")
    parser.add_argument("--intervalo", type=float, default=0.05, help="pausa entre mensagens de um cliente, em s")
    parser.add_argument("--canal", choices=["ws", "udp"], default="ws")
    # Modo interno: o script chama a si mesmo para cada cliente.
    parser.add_argument("--cliente", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--device-id", help=argparse.SUPPRESS)
    parser.add_argument("--token", help=argparse.SUPPRESS)
    args = parser.parse_args()

    if args.cliente:
        if args.canal == "ws":
            asyncio.run(cliente_ws(args.device_id, args.token, args.mensagens, args.intervalo))
        else:
            cliente_udp(args.device_id, args.token, args.mensagens, args.intervalo)
        return

    args.clientes = [int(c) for c in args.clientes.split(",")]
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
