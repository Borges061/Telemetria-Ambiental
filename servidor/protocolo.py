
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class MensagemLeitura(BaseModel):
    tipo: Literal["leitura"]
    device_id: str = Field(min_length=1)
    token: str = Field(min_length=1)
    timestamp: datetime
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
