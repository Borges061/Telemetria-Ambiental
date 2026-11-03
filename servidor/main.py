"""
Responsável por inicializar a aplicação FastAPI e disponibilizar
as rotas HTTP e WebSocket utilizadas pelo sistema.

"""
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Literal

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field, model_validator

from servidor.auth import autenticar_dispositivo, cadastrar_dispositivo
from servidor.conexoes import (
    JANELA_ATIVIDADE_UDP_SEGUNDOS,
    gerenciador,
)
from servidor.db import (
    get_limiar,
    inicializar_banco,
    listar_alertas,
    listar_leituras,
    salvar_alerta,
    salvar_leitura,
    set_limiar,
)
from servidor.log_config import configurar_logs
from servidor.protocolo import msg_alerta, msg_erro, msg_update, validar_leitura
from servidor.udp_server import iniciar_udp


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configurar_logs()
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


class ConfiguracaoLimiar(BaseModel):
    metrica: Literal["temperatura", "umidade", "qualidade_ar"]
    valor_max: float | None = Field(default=None, allow_inf_nan=False)
    valor_min: float | None = Field(default=None, allow_inf_nan=False)
    nivel: Literal["critico"] = "critico"

    @model_validator(mode="after")
    def validar_limites(self):
        if self.valor_max is None and self.valor_min is None:
            raise ValueError(
                "Informe pelo menos um limite mínimo ou máximo."
            )

        if (
            self.valor_max is not None
            and self.valor_min is not None
            and self.valor_min >= self.valor_max
        ):
            raise ValueError(
                "O limite mínimo deve ser menor que o máximo."
            )

        return self


def verificar_limiar(metrica, valor):
    """
    Verifica se uma leitura ultrapassou os limites configurados.

    Retorna o limite violado ou None se o valor estiver normal.
    """

    limiar = get_limiar(metrica)

    if limiar is None:
        return None

    valor_max = limiar["valor_max"]
    valor_min = limiar["valor_min"]

    if valor_max is not None and valor > valor_max:
        return valor_max

    if valor_min is not None and valor < valor_min:
        return valor_min

    return None


async def processar_leitura(
    raw: object,
    *,
    via_udp: bool = False
) -> dict[str, str] | None:
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

    if via_udp:
        gerenciador.registrar_leitura_udp(leitura.device_id)

    atualizacao = msg_update(leitura)

    await gerenciador.transmitir_paineis(atualizacao)

    # Verifica se a leitura ultrapassou algum limite.
    limite_violado = verificar_limiar(leitura.metrica, leitura.valor)

    if limite_violado is not None:
        configuracao = get_limiar(leitura.metrica)
        nivel = configuracao["nivel"]

        # Registra o alerta no banco de dados.
        salvar_alerta(
            leitura.device_id,
            leitura.metrica,
            leitura.valor,
            limite_violado,
            nivel,
            leitura.timestamp.isoformat()
        )

        # Monta a mensagem de alerta para o painel.
        alerta = msg_alerta(
            leitura,
            limite_violado,
            nivel
        )

        # Envia o alerta aos painéis conectados.
        await gerenciador.transmitir_paineis(alerta)

    return None


async def processar_leitura_udp(
    dados: object,
    origem: str
) -> None:
    erro = await processar_leitura(dados, via_udp=True)
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
    sensores_websocket, sensores_udp = gerenciador.contagem_sensores()

    return {
        "status": "online",
        "uptime_segundos": round(uptime, 2),
        "sensores_conectados": sensores_websocket + sensores_udp,
        "sensores_websocket_conectados": sensores_websocket,
        "sensores_udp_ativos": sensores_udp,
        "janela_atividade_udp_segundos": JANELA_ATIVIDADE_UDP_SEGUNDOS
    }

@app.get("/api/ping")
def verificar_ping():
    return {
        "pong": True,
        "t_servidor": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/alertas")
def consultar_alertas():
    """
    Retorna os alertas registrados no banco de dados.
    """
    return listar_alertas()

@app.get("/api/leituras")
def obter_leituras(
    device_id: str | None = Query(default=None, min_length=1),
    device: str | None = Query(default=None, min_length=1),
    metrica: str | None = Query(default=None, min_length=1),
    limite: int = Query(default=100, ge=1, le=1000),
):
    return listar_leituras(
        device=device_id or device,
        metrica=metrica,
        limite=limite
    )


@app.post("/api/dispositivos", status_code=201)
def registrar_dispositivo(dados: CadastroDispositivo):
    return cadastrar_dispositivo(dados.nome)

@app.put("/api/limiares")
def atualizar_limiar(dados: ConfiguracaoLimiar):
    set_limiar(
        dados.metrica,
        dados.valor_max,
        dados.valor_min,
        dados.nivel
    )

    return get_limiar(dados.metrica)

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

            erro = await processar_leitura(dados)

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