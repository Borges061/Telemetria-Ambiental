
"""
Módulo de gerenciamento das conexões WebSocket.

Responsável por registrar e remover conexões de sensores
e painéis, transmitir mensagens aos painéis conectados
e informar a quantidade de conexões ativas no servidor.
"""

import threading
import time

from fastapi import WebSocket

JANELA_ATIVIDADE_UDP_SEGUNDOS = 10


class GerenciadorConexoes:
    """
    Gerencia as conexões WebSocket mantidas pelo servidor.

    Mantém dois conjuntos de conexões:
        paineis: Clientes que recebem atualizações em tempo real.
        sensores: Dispositivos que enviam leituras ao servidor.

    Sensores UDP são considerados ativos durante a janela definida
    desde a última leitura válida e autenticada recebida.

    Também fornece métodos para aceitar conexões, remover
    clientes desconectados e transmitir mensagens aos painéis.
    """


    def __init__(self):
        self.paineis: set[WebSocket] = set()
        self.sensores: set[WebSocket] = set()
        self.ultimas_leituras_udp: dict[str, float] = {}
        self._lock = threading.Lock()

    async def conectar_painel(self, websocket: WebSocket):
        await websocket.accept()
        with self._lock:
            self.paineis.add(websocket)

    async def conectar_sensor(self, websocket: WebSocket):
        await websocket.accept()
        with self._lock:
            self.sensores.add(websocket)

    def desconectar_painel(self, websocket: WebSocket):
        with self._lock:
            self.paineis.discard(websocket)

    def desconectar_sensor(self, websocket: WebSocket):
        with self._lock:
            self.sensores.discard(websocket)

    async def transmitir_paineis(self, mensagem: dict):
        with self._lock:
            paineis = list(self.paineis)

        for painel in paineis:
            try:
                await painel.send_json(mensagem)
            except Exception:
                self.desconectar_painel(painel)

    def registrar_leitura_udp(self, device_id: str):
        agora = time.monotonic()
        with self._lock:
            self._remover_sensores_udp_expirados(agora)
            self.ultimas_leituras_udp[device_id] = agora

    def _remover_sensores_udp_expirados(self, agora: float):
        limite = agora - JANELA_ATIVIDADE_UDP_SEGUNDOS
        self.ultimas_leituras_udp = {
            device_id: recebida_em
            for device_id, recebida_em in self.ultimas_leituras_udp.items()
            if recebida_em > limite
        }

    def contagem_sensores(self) -> tuple[int, int]:
        agora = time.monotonic()

        with self._lock:
            self._remover_sensores_udp_expirados(agora)
            return len(self.sensores), len(self.ultimas_leituras_udp)

    def total_sensores_conectados(self):
        sensores_websocket, sensores_udp = self.contagem_sensores()
        return sensores_websocket + sensores_udp

# Instância compartilhada utilizada pelas rotas do servidor.

gerenciador = GerenciadorConexoes()
