"""
Funções compartilhadas pelos scripts de experimento.

Lê os endereços do servidor das mesmas variáveis de ambiente usadas no
compose.yaml, cadastra dispositivos, monta leituras no formato do
protocolo e grava os resultados em CSV dentro de resultados/.
"""

import asyncio
import csv
import json
import os
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
WS_URL = os.getenv("WS_URL", "ws://localhost:8000/ws/sensor")
WS_PAINEL_URL = os.getenv(
    "WS_PAINEL_URL",
    WS_URL.replace("/ws/sensor", "/ws/painel")
)
UDP_HOST = os.getenv("UDP_HOST", "127.0.0.1")
UDP_PORT = int(os.getenv("UDP_PORT", "9999"))

RESULTADOS = Path(
    os.getenv("RESULTADOS_DIR", str(Path(__file__).resolve().parent / "resultados"))
)


def cadastrar(nome):
    """Cadastra um dispositivo e devolve (device_id, token)."""
    resposta = requests.post(
        f"{API_BASE_URL}/api/dispositivos",
        json={"nome": nome},
        timeout=5
    )
    resposta.raise_for_status()
    dados = resposta.json()
    return dados["device_id"], dados["token"]


def montar_leitura(device_id, token, seq, tamanho=None):
    """
    Monta uma leitura JSON do protocolo.

    Se `tamanho` for informado, completa a mensagem com o campo
    `padding` (ignorado pelo servidor) até ter exatamente `tamanho` bytes.
    O valor fica dentro da faixa normal para não gerar alertas.
    """
    mensagem = {
        "tipo": "leitura",
        "device_id": device_id,
        "token": token,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrica": "temperatura",
        "valor": 25.0,
        "unidade": "C",
        "seq": seq,
    }

    if tamanho:
        mensagem["padding"] = ""
        base = len(json.dumps(mensagem).encode("utf-8"))
        mensagem["padding"] = "x" * max(0, tamanho - base)

    return json.dumps(mensagem).encode("utf-8")


async def coletar_updates(painel, device_ids, esperado, ocioso=3.0):
    """
    Lê mensagens `update` do /ws/painel dos dispositivos informados.

    Para quando recebe `esperado` mensagens ou quando fica `ocioso`
    segundos sem receber nada. Devolve uma lista de
    (instante_perf_counter, instante_utc, mensagem).
    """
    device_ids = set(device_ids)
    chegadas = []

    while len(chegadas) < esperado:
        try:
            bruto = await asyncio.wait_for(painel.recv(), ocioso)
        except asyncio.TimeoutError:
            break

        mensagem = json.loads(bruto)
        if (
            mensagem.get("tipo") == "update"
            and mensagem.get("device_id") in device_ids
        ):
            chegadas.append(
                (time.perf_counter(), datetime.now(timezone.utc), mensagem)
            )

    return chegadas


def diferenca_ms(fim_iso, inicio_iso):
    fim = datetime.fromisoformat(fim_iso)
    inicio = datetime.fromisoformat(inicio_iso)
    return (fim - inicio).total_seconds() * 1000


def resumo(valores):
    """Média, mediana, desvio padrão populacional, mínimo e máximo."""
    valores = [v for v in valores if v is not None]
    if not valores:
        return {"n": 0}
    return {
        "n": len(valores),
        "media": statistics.mean(valores),
        "mediana": statistics.median(valores),
        "desvio": statistics.pstdev(valores),
        "min": min(valores),
        "max": max(valores),
    }


def imprimir_resumo(rotulo, valores, unidade="ms"):
    r = resumo(valores)
    if r["n"] == 0:
        print(f"{rotulo}: sem amostras válidas")
        return
    print(
        f"{rotulo}: n={r['n']} média={r['media']:.3f}{unidade} "
        f"mediana={r['mediana']:.3f}{unidade} desvio={r['desvio']:.3f}{unidade} "
        f"min={r['min']:.3f}{unidade} max={r['max']:.3f}{unidade}"
    )


def salvar_csv(nome_arquivo, linhas):
    """Grava uma lista de dicionários em resultados/<nome_arquivo>."""
    RESULTADOS.mkdir(parents=True, exist_ok=True)
    caminho = RESULTADOS / nome_arquivo

    if not linhas:
        print(f"Nada para salvar em {caminho}")
        return caminho

    with open(caminho, "w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=list(linhas[0].keys()))
        escritor.writeheader()
        escritor.writerows(linhas)

    print(f"Resultados salvos em {caminho}")
    return caminho
