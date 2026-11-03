
import asyncio
import argparse
import json
import logging

from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed

from sensores.sensor_temperatura import SensorTemperatura


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)


async def executar_sensor(device_id, token, url, intervalo):
    sensor = SensorTemperatura(device_id, token)

    while True:
        try:
            logging.info("Conectando ao servidor: %s", url)

            async with connect(
                url,
                open_timeout=10,
                ping_interval=20,
                ping_timeout=20
            ) as websocket:

                logging.info(
                    "Sensor %s conectado",
                    device_id
                )

                while True:
                    leitura = sensor.gerar_leitura()

                    mensagem = json.dumps(leitura)

                    await websocket.send(mensagem)

                    logging.info(
                        "Enviado: %s",
                        mensagem
                    )

                    await asyncio.sleep(intervalo)

        except (
            OSError,
            ConnectionClosed,
            TimeoutError
        ) as erro:
            logging.warning(
                "Conexão interrompida: %s",
                erro
            )

            logging.info(
                "Tentando reconectar em 5 segundos..."
            )

            await asyncio.sleep(5)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--device-id",
        required=True
    )

    parser.add_argument(
        "--token",
        required=True
    )

    parser.add_argument(
        "--url",
        default="ws://localhost:8000/ws/sensor"
    )

    parser.add_argument(
        "--intervalo",
        type=float,
        default=2.0
    )

    args = parser.parse_args()

    if args.intervalo <= 0:
        parser.error("--intervalo deve ser maior que zero")

    try:
        asyncio.run(
            executar_sensor(
                args.device_id,
                args.token,
                args.url,
                args.intervalo
            )
        )
    except KeyboardInterrupt:
        logging.info("Sensor encerrado")


if __name__ == "__main__":
    main()
