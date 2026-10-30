"""
Responsável por inicializar a aplicação FastAPI e disponibilizar
as rotas HTTP e WebSocket utilizadas pelo sistema.

"""
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Literal

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel, Field, model_validator

from auth import cadastrar_dispositivo, autenticar_dispositivo
from conexoes import gerenciador
from db import (
    init_db,
    salvar_leitura,
    salvar_alerta,
    get_limiar,
    set_limiar,
    listar_alertas,
    listar_leituras,
)
from protocolo import validar_leitura, msg_update, msg_alerta, msg_erro
from log_config import configurar_logs
from udp_server import iniciar_udp
# Instância principal da aplicação FastAPI.

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicializa as tabelas do banco de dados.
    init_db()

    # Configura o registro de logs.
    configurar_logs()

    # Obtém o event loop utilizado pelo FastAPI.
    loop = asyncio.get_running_loop()

    # Inicia a escuta de sensores UDP.
    iniciar_udp(processar_leitura, loop)

    yield


# Instância principal da aplicação FastAPI.
app = FastAPI(lifespan=lifespan)

inicio_servidor = datetime.now(timezone.utc)
clientes_conectados = 0

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

@app.get("/api/status")
def verificar_status():
    agora = datetime.now(timezone.utc)
    uptime = (agora - inicio_servidor).total_seconds()

    return {
        "status": "online",
        "uptime_segundos": round(uptime, 2),
        "clientes_conectados": gerenciador.total_conectados()
    }

@app.get("/api/alertas")
def consultar_alertas():
    """
    Retorna os alertas registrados no banco de dados.
    """
    return listar_alertas()

@app.get("/api/leituras")
def consultar_leituras(
    device: str | None = None,
    metrica: str | None = None,
    limite: int = Query(default=100, ge=1, le=1000)):
    """
    Consulta as leituras armazenadas no SQLite,
    permitindo filtrar por dispositivo e métrica.
    """
    return listar_leituras(
        device=device,
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