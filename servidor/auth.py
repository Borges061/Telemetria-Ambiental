
"""
Módulo de cadastro e autenticação de dispositivos.

gera identificadores e tokens para novos
sensores, armazenar suas credenciais no banco SQLite e
valida a identidade dos dispositivos durante a comunicação
com o servidor.

"""

import secrets
import uuid
from datetime import datetime, timezone
import db


def cadastrar_dispositivo(nome):
    device_id = f"sensor-{uuid.uuid4().hex[:8]}"
    token = secrets.token_hex(16)
    criado_em = datetime.now(timezone.utc).isoformat()

    db.criar_dispositivo(device_id, token, nome, criado_em)

    return {
        "device_id": device_id,
        "token": token,
        "nome": nome
    }


def autenticar_dispositivo(device_id, token):
    dispositivo = db.buscar_dispositivo(device_id)

    if dispositivo is None:
        return False

    return secrets.compare_digest(dispositivo["token"], token)
