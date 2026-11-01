import asyncio
import json
import logging
import os
import socket
import threading


def iniciar_udp(processar_coro, loop: asyncio.AbstractEventLoop) -> threading.Thread:
    """
    processar_coro: async def processar_leitura(raw: dict, origem: str) do main.py.
    loop:           event loop do FastAPI, capturado no startup.
    Retorna a thread já iniciada (daemon=True).
    """
    host = os.getenv("UDP_HOST", "0.0.0.0")
    port = int(os.getenv("UDP_PORT", "9999"))
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, port))
    logging.info("UDP escutando em %s:%d", host, port)

    def _resultado(origem):
        def _cb(fut):
            try:
                erro = fut.result()
            except Exception:
                logging.exception("UDP: falha ao processar leitura de %s", origem)
                return
            if erro:
                logging.warning("UDP: leitura rejeitada de %s: %s", origem, erro["codigo"])
        return _cb

    def _loop_recv():
        while True:
            addr = None
            try:
                data, addr = sock.recvfrom(65535)
                raw = json.loads(data.decode("utf-8"))
                origem = f"udp:{addr[0]}"
                fut = asyncio.run_coroutine_threadsafe(processar_coro(raw, origem), loop)
                fut.add_done_callback(_resultado(origem))
            except (json.JSONDecodeError, UnicodeDecodeError):
                logging.warning("UDP: datagrama malformado de %s", addr)
            except Exception as e:
                logging.exception("UDP: erro inesperado: %s", e)

    t = threading.Thread(target=_loop_recv, name="udp-server", daemon=True)
    t.start()
    return t
