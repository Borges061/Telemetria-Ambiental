
"""
Módulo de gerenciamento das conexões WebSocket.

Responsável por registrar e remover conexões de sensores
e painéis, transmitir mensagens aos painéis conectados
e informar a quantidade de conexões ativas no servidor.
"""

from fastapi import WebSocket


class GerenciadorConexoes:
    """
    Gerencia as conexões WebSocket mantidas pelo servidor.

    Mantém dois conjuntos de conexões:
        paineis: Clientes que recebem atualizações em tempo real.
        sensores: Dispositivos que enviam leituras ao servidor.

    Também fornece métodos para aceitar conexões, remover
    clientes desconectados e transmitir mensagens aos painéis.
    """


    def __init__(self):
        self.paineis: set[WebSocket] = set()
        self.sensores: set[WebSocket] = set()

    async def conectar_painel(self, websocket: WebSocket):
        await websocket.accept()
        self.paineis.add(websocket)

    async def conectar_sensor(self, websocket: WebSocket):
        await websocket.accept()
        self.sensores.add(websocket)

    def desconectar_painel(self, websocket: WebSocket):
        self.paineis.discard(websocket)

    def desconectar_sensor(self, websocket: WebSocket):
        self.sensores.discard(websocket)

    async def transmitir_paineis(self, mensagem: dict):
        for painel in list(self.paineis):
            try:
                await painel.send_json(mensagem)
            except Exception:
                self.desconectar_painel(painel)

    def total_conectados(self):
        return len(self.paineis) + len(self.sensores)

# Instância compartilhada utilizada pelas rotas do servidor.

gerenciador = GerenciadorConexoes()
