import random
import math
import time
from datetime import datetime, timezone


class SensorTemperatura:
    def __init__(self, device_id, token, valor_base=25.0):
        self.device_id = device_id
        self.token = token
        self.valor_base = valor_base
        self.seq = 0

    def gerar_leitura(self):
        self.seq += 1

        # Oscilação gradualx
        oscilacao = 3 * math.sin(self.seq / 10)

        # Ruído aleatório
        ruido = random.gauss(0, 0.3)

        temperatura = self.valor_base + oscilacao + ruido

        # Evento anormal ocasional
        if random.random() < 0.03:
            temperatura += 12


        return {
                    "tipo": "leitura",
                    "device_id": self.device_id,
                    "token": self.token,
                    "timestamp": datetime.now(
                        timezone.utc
                    ).isoformat(),
                    "metrica": "temperatura",
                    "valor": round(temperatura, 2),
                    "unidade": "ºC",
                    "seq": self.seq
                }
    

#Para Teste
'''sensor = SensorTemperatura("id sensor","token")

while True:
    leitura = sensor.gerar_leitura()
    print(leitura)
    time.sleep(2)'''
