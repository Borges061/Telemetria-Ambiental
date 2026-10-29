
from datetime import datetime, timezone
from fastapi import FastAPI
from pydantic import BaseModel, Field
from servidor.auth import cadastrar_dispositivo
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from servidor.auth import autenticar_dispositivo
from servidor.db import salvar_leitura
from servidor.protocolo import MensagemLeitura
from servidor.conexoes import gerenciador

app = FastAPI()

inicio_servidor = datetime.now(timezone.utc)
clientes_conectados = 0


class CadastroDispositivo(BaseModel):
    nome: str = Field(min_length=1)


@app.get("/api/status")
def verificar_status():
    agora = datetime.now(timezone.utc)
    uptime = (agora - inicio_servidor).total_seconds()

    return {
        "status": "online",
        "uptime_segundos": round(uptime, 2),
        "clientes_conectados": gerenciador.total_conectados()
    }


@app.post("/api/dispositivos", status_code=201)
def registrar_dispositivo(dados: CadastroDispositivo):
    return cadastrar_dispositivo(dados.nome)



@app.websocket("/ws/painel")
async def websocket_painel(websocket: WebSocket):
    await gerenciador.conectar_painel(websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        gerenciador.desconectar_painel(websocket)


@app.websocket("/ws/sensor")
async def websocket_sensor(websocket: WebSocket):
    await gerenciador.conectar_sensor(websocket)

    try:
        while True:
            dados = await websocket.receive_json()

            try:
                leitura = MensagemLeitura.model_validate(dados)
            except ValidationError:
                await websocket.send_json({
                    "tipo": "erro",
                    "codigo": "FORMATO_INVALIDO",
                    "mensagem": "Mensagem JSON inválida",
                    "seq": dados.get("seq") if isinstance(dados, dict) else None
                })
                continue

            if not autenticar_dispositivo(
                leitura.device_id,
                leitura.token
            ):
                await websocket.send_json({
                    "tipo": "erro",
                    "codigo": "TOKEN_INVALIDO",
                    "mensagem": "Dispositivo não autenticado",
                    "seq": leitura.seq
                })
                continue

            salvar_leitura(
                leitura.device_id,
                leitura.metrica,
                leitura.valor,
                leitura.unidade,
                leitura.timestamp.isoformat(),
                leitura.seq
            )

            atualizacao = {
                "tipo": "update",
                "device_id": leitura.device_id,
                "metrica": leitura.metrica,
                "valor": leitura.valor,
                "unidade": leitura.unidade,
                "timestamp": leitura.timestamp.isoformat()
            }

            await gerenciador.transmitir_paineis(atualizacao)

    except WebSocketDisconnect:
        pass
    finally:
        gerenciador.desconectar_sensor(websocket)
