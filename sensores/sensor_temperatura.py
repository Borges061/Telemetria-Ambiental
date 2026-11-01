import random
import math
import time
from datetime import datetime, timezone


class SensorSimulado:
    def __init__(self, device_id, valor_base=25.0):
        self.device_id = device_id
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

        '''return {
            "device_id": self.device_id,
            "seq": self.seq,
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
            "temperatura": round(temperatura, 2)
        }'''

        return {
                    "tipo": "leitura",
                    "device_id": self.device_id,
                    "token": "16221a10743621550b3f7445f5bc471e",
                    "timestamp": datetime.now(
                        timezone.utc
                    ).isoformat(),
                    "metrica": "temperatura",
                    "valor": round(temperatura, 2),
                    "unidade": "ºC",
                    "seq": self.seq
                }
    

#Para Teste
'''sensor = SensorSimulado("sensor-4ff600df")

while True:
    leitura = sensor.gerar_leitura()
    print(leitura)
    time.sleep(2)'''
