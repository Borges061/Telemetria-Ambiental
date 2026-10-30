

"""
Módulo de definição e validação do protocolo de comunicação.

Define a estrutura das mensagens de leitura enviadas pelos
sensores ao servidor, utilizando Pydantic para verificar
os campos obrigatórios e seus respectivos tipos.

"""


from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

METRICAS_PERMITIDAS = {
    "temperatura",
    "umidade",
    "qualidade_ar"
}

class MensagemLeitura(BaseModel):
    #tipo de mensagem permitida pelo protocolo
    tipo: Literal["leitura"]
    #identificação e autenticação dos dispositivos
    device_id: str = Field(min_length=1)
    token: str = Field(min_length=1)
    timestamp: datetime
    #informações de grandeza monitorada
    metrica: str = Field(min_length=1)
    valor: float
    unidade: str = Field(min_length=1)
    seq: int = Field(ge=0)

    @field_validator("timestamp")
    @classmethod
    def validar_fuso_horario(cls, valor):
        if valor.tzinfo is None or valor.utcoffset() is None:
            raise ValueError("Timestamp deve conter fuso horário")
        return valor

    @field_validator("metrica")
    @classmethod
    def validar_metrica(cls, valor):
        if valor not in METRICAS_PERMITIDAS:
            raise ValueError("Métrica desconhecida")
        return valor

def validar_leitura(raw):
    """
    Valida uma mensagem recebida de um sensor.

    Retorna:
        (mensagem, None), se a leitura for válida.
        (None, erro), se a leitura for inválida.
    """

    if not isinstance(raw, dict):
        return None, {
            "codigo": "FORMATO_INVALIDO",
            "mensagem": "A mensagem deve ser um objeto JSON."
        }

    try:
        mensagem = MensagemLeitura.model_validate(raw)
        return mensagem, None

    except ValidationError as exc:
        erros = exc.errors()

        if any(erro["type"] == "missing" for erro in erros):
            codigo = "CAMPO_FALTANDO"
            descricao = "A mensagem não contém todos os campos obrigatórios."

        elif any(
            erro["loc"] == ("metrica",) and erro["type"] == "value_error"
            for erro in erros
        ):
            codigo = "METRICA_DESCONHECIDA"
            descricao = "A métrica informada não é reconhecida."

        else:
            codigo = "VALOR_INVALIDO"
            descricao = "Um ou mais campos possuem valores inválidos."

        return None, {
            "codigo": codigo,
            "mensagem": descricao
        }


def msg_update(leitura):
    """Cria a mensagem de atualização enviada ao painel."""
    return {
        "tipo": "update",
        "device_id": leitura.device_id,
        "metrica": leitura.metrica,
        "valor": leitura.valor,
        "unidade": leitura.unidade,
        "timestamp": leitura.timestamp.isoformat()
    }

def msg_alerta(leitura, limiar, nivel):
    """Cria uma mensagem de alerta para o painel."""
    return {
        "tipo": "alerta",
        "device_id": leitura.device_id,
        "metrica": leitura.metrica,
        "valor": leitura.valor,
        "limiar": limiar,
        "nivel": nivel,
        "timestamp": leitura.timestamp.isoformat()
    }

def msg_erro(codigo, mensagem, seq=None):
    """Cria uma mensagem de erro do protocolo."""
    return {
        "tipo": "erro",
        "codigo": codigo,
        "mensagem": mensagem,
        "seq": seq
    }