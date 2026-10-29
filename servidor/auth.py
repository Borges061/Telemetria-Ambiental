
import secrets
import uuid
from datetime import datetime, timezone

from servidor.db import conectar


def cadastrar_dispositivo(nome):
    device_id = f"sensor-{uuid.uuid4().hex[:8]}"
    token = secrets.token_hex(16)
    criado_em = datetime.now(timezone.utc).isoformat()

    with conectar() as conexao:
        conexao.execute(
            """
            INSERT INTO dispositivos
            (device_id, token, nome, criado_em)
            VALUES (?, ?, ?, ?)
            """,
            (device_id, token, nome, criado_em)
        )

    return {
        "device_id": device_id,
        "token": token
    }


def autenticar_dispositivo(device_id, token):
    with conectar() as conexao:
        dispositivo = conexao.execute(
            """
            SELECT device_id
            FROM dispositivos
            WHERE device_id = ? AND token = ?
            """,
            (device_id, token)
        ).fetchone()

    return dispositivo is not None
