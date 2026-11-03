import argparse
import json
import logging
import os
import socket
import time

if __package__:
    from .sensor_umidade import SensorUmidade
else:
    from sensor_umidade import SensorUmidade


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)


def executar_sensor(device_id, token, host, porta, intervalo):
    sensor = SensorUmidade(device_id, token)
    destino = (host, porta)

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        while True:
            leitura = sensor.gerar_leitura()
            mensagem = json.dumps(leitura).encode("utf-8")
            sock.sendto(mensagem, destino)
            logging.info(
                "Leitura enviada para %s:%d: seq=%d umidade=%.2f%%",
                host,
                porta,
                leitura["seq"],
                leitura["valor"],
            )
            time.sleep(intervalo)


def main():
    parser = argparse.ArgumentParser(description="Envia leituras simuladas de umidade por UDP.")
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--token", default=os.getenv("SENSOR_TOKEN"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--porta", type=int, default=9999)
    parser.add_argument("--intervalo", type=float, default=2.0)
    args = parser.parse_args()

    if not args.token:
        parser.error("informe --token ou defina a variável de ambiente SENSOR_TOKEN")
    if not 1 <= args.porta <= 65535:
        parser.error("--porta deve estar entre 1 e 65535")
    if args.intervalo <= 0:
        parser.error("--intervalo deve ser maior que zero")

    try:
        executar_sensor(
            args.device_id,
            args.token,
            args.host,
            args.porta,
            args.intervalo,
        )
    except KeyboardInterrupt:
        logging.info("Sensor encerrado")


if __name__ == "__main__":
    main()
