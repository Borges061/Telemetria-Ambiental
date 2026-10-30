"""
Responsável por inicializar a aplicação FastAPI e disponibilizar
as rotas HTTP e WebSocket utilizadas pelo sistema.

"""


from datetime import datetime, timezone

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from auth import cadastrar_dispositivo, autenticar_dispositivo
from db import salvar_leitura
from protocolo import validar_leitura, msg_update, msg_erro
from conexoes import gerenciador
# Instância principal da aplicação FastAPI.

app = FastAPI()

inicio_servidor = datetime.now(timezone.utc)
clientes_conectados = 0


class CadastroDispositivo(BaseModel):
    nome: str = Field(min_length=1)

async def processar_leitura(raw, origem):
    """
    Processa uma leitura recebida por WebSocket ou UDP.

    Retorna None em caso de sucesso.
    Retorna um dicionário de erro se a leitura for rejeitada.
    """

    leitura, erro = validar_leitura(raw)

    if erro is not None:
        return erro

    if not autenticar_dispositivo(leitura.device_id, leitura.token):
        return {
            "codigo": "TOKEN_INVALIDO",
            "mensagem": "Dispositivo não autenticado"
        }

    salvar_leitura(
        leitura.device_id,
        leitura.metrica,
        leitura.valor,
        leitura.unidade,
        leitura.timestamp.isoformat(),
        leitura.seq
    )

    atualizacao = msg_update(leitura)

    await gerenciador.transmitir_paineis(atualizacao)

    return None

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
            # Mantém a conexão aberta aguardando mensagens.
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
            try:
                dados = await websocket.receive_json()
            except WebSocketDisconnect:
                raise
            except ValueError:
                await websocket.send_json(
                    msg_erro(
                        "FORMATO_INVALIDO",
                        "Mensagem JSON inválida"
                    )
                )
                continue

            erro = await processar_leitura(dados, "websocket")

            if erro is not None:
                seq = dados.get("seq") if isinstance(dados, dict) else None

                await websocket.send_json(
                    msg_erro(
                        erro["codigo"],
                        erro["mensagem"],
                        seq
                    )
                )

    except WebSocketDisconnect:
        pass
    finally:
        gerenciador.desconectar_sensor(websocket)