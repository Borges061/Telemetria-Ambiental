import math
import random
from datetime import datetime, timezone


class SensorUmidade:
    def __init__(self, device_id, token, valor_base=55.0):
        self.device_id = device_id
        self.token = token
        self.valor_base = valor_base
        self.seq = 0

    def gerar_leitura(self):
        self.seq += 1
        oscilacao = 12 * math.sin(self.seq / 10)
        ruido = random.gauss(0, 1.5)
        umidade = max(0.0, min(100.0, self.valor_base + oscilacao + ruido))

        return {
            "tipo": "leitura",
            "device_id": self.device_id,
            "token": self.token,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrica": "umidade",
            "valor": round(umidade, 2),
            "unidade": "%",
            "seq": self.seq,
        }