import logging


def configurar_logs():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
        handlers=[logging.StreamHandler(),
                  logging.FileHandler("servidor.log", encoding="utf-8")],
        force=True,
    )
