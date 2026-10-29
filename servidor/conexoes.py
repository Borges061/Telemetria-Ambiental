
from fastapi import WebSocket


class GerenciadorConexoes:
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


gerenciador = GerenciadorConexoes()
