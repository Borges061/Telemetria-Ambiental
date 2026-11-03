"""
Responsável por inicializar a aplicação FastAPI e disponibilizar
as rotas HTTP e WebSocket utilizadas pelo sistema.

"""


import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, Query
from pydantic import BaseModel, Field
from servidor.auth import cadastrar_dispositivo
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from servidor.auth import autenticar_dispositivo
from servidor.db import listar_leituras, salvar_leitura
from servidor.protocolo import MensagemLeitura
from servidor.conexoes import gerenciador
from servidor.udp_server import iniciar_udp
# Instância principal da aplicação FastAPI.


@asynccontextmanager
async def lifespan(_app: FastAPI):
    from servidor.db import inicializar_banco

    inicializar_banco()
    parar_udp = iniciar_udp(processar_leitura_udp, asyncio.get_running_loop())
    try:
        yield
    finally:
        parar_udp()


app = FastAPI(lifespan=lifespan)

inicio_servidor = datetime.now(timezone.utc)


class CadastroDispositivo(BaseModel):
    nome: str = Field(min_length=1)


async def processar_leitura(dados: object) -> dict[str, object] | None:
    try:
        leitura = MensagemLeitura.model_validate(dados)
    except ValidationError:
        return {
            "tipo": "erro",
            "codigo": "FORMATO_INVALIDO",
            "mensagem": "Mensagem JSON inválida",
            "seq": dados.get("seq") if isinstance(dados, dict) else None
        }

    if not autenticar_dispositivo(leitura.device_id, leitura.token):
        return {
            "tipo": "erro",
            "codigo": "TOKEN_INVALIDO",
            "mensagem": "Dispositivo não autenticado",
            "seq": leitura.seq
        }

    leitura_id = salvar_leitura(
        leitura.device_id,
        leitura.metrica,
        leitura.valor,
        leitura.unidade,
        leitura.timestamp.isoformat(),
        leitura.seq
    )

    atualizacao = {
        "tipo": "update",
        "id": leitura_id,
        "device_id": leitura.device_id,
        "metrica": leitura.metrica,
        "valor": leitura.valor,
        "unidade": leitura.unidade,
        "timestamp": leitura.timestamp.isoformat()
    }

    await gerenciador.transmitir_paineis(atualizacao)
    return None


async def processar_leitura_udp(
    dados: object,
    origem: str
) -> None:
    erro = await processar_leitura(dados)
    if erro is not None:
        logging.warning(
            "UDP: leitura rejeitada de %s: %s",
            origem,
            erro["codigo"]
        )


@app.get("/api/status")
def verificar_status():
    agora = datetime.now(timezone.utc)
    uptime = (agora - inicio_servidor).total_seconds()

    return {
        "status": "online",
        "uptime_segundos": round(uptime, 2),
        "sensores_conectados": gerenciador.total_sensores_conectados()
    }


@app.get("/api/leituras")
def obter_leituras(
    device_id: str | None = Query(default=None, min_length=1),
    metrica: str | None = Query(default=None, min_length=1),
    limite: int = Query(default=50, ge=1, le=500),
):
    return listar_leituras(device=device_id, metrica=metrica, limite=limite)


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
            dados = await websocket.receive_json()
            erro = await processar_leitura(dados)
            if erro is not None:
                await websocket.send_json(erro)

    except WebSocketDisconnect:
        pass
    finally:
        gerenciador.desconectar_sensor(websocket)
