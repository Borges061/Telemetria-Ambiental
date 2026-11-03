import asyncio
import json
import logging
import os
import socket
import threading
from collections.abc import Awaitable, Callable


def iniciar_udp(
    processar_coro: Callable[
        [object, str],
        Awaitable[dict[str, object] | None]
    ],
    loop: asyncio.AbstractEventLoop
) -> Callable[[], None]:
    """
    Inicia o listener UDP e retorna uma função para encerrá-lo.
    """
    host = os.getenv("UDP_HOST", "0.0.0.0")
    port = int(os.getenv("UDP_PORT", "9999"))
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind((host, port))
        sock.settimeout(0.5)
    except OSError:
        sock.close()
        raise
    parar = threading.Event()
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
        try:
            while not parar.is_set():
                addr = None
                try:
                    data, addr = sock.recvfrom(65535)
                except socket.timeout:
                    continue
                except OSError:
                    if not parar.is_set():
                        logging.exception("UDP: erro ao receber datagrama")
                    break

                origem = f"udp:{addr[0]}"
                try:
                    raw = json.loads(data.decode("utf-8"))
                    fut = asyncio.run_coroutine_threadsafe(
                        processar_coro(raw, origem),
                        loop
                    )
                    fut.add_done_callback(_resultado(origem))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    logging.warning("UDP: datagrama malformado de %s", addr)
                except Exception:
                    logging.exception("UDP: erro inesperado ao processar datagrama de %s", addr)
        finally:
            sock.close()

    t = threading.Thread(target=_loop_recv, name="udp-server", daemon=True)
    t.start()

    def encerrar():
        parar.set()
        t.join()

    return encerrar
