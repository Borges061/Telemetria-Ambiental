"""
Experimento A: tempo de resposta (RTT) da aplicação.

Faz N requisições GET /api/ping e mede o tempo entre o envio da
requisição e a chegada da resposta, do ponto de vista do cliente.

Uso:
    python exp_a_rtt.py --n 50 --condicao local
    python exp_a_rtt.py --n 50 --condicao local_sem_keepalive --nova-conexao
"""

import argparse
import time

import requests

from comum import API_BASE_URL, imprimir_resumo, salvar_csv


def medir_rtt(n, intervalo=0.1, nova_conexao=False, condicao="local"):
    """
    Mede o RTT de N requisições a /api/ping.

    Com `nova_conexao`, cada requisição abre uma conexão TCP nova
    (inclui o 3-way handshake no tempo medido). Sem ela, a mesma
    conexão é reaproveitada (keep-alive).
    """
    url = f"{API_BASE_URL}/api/ping"
    sessao = requests.Session()

    # Primeira requisição só aquece a conexão e não entra na medição.
    try:
        sessao.get(url, timeout=5)
    except requests.RequestException:
        pass

    linhas = []
    for i in range(1, n + 1):
        cliente = requests if nova_conexao else sessao
        inicio = time.perf_counter()
        try:
            resposta = cliente.get(url, timeout=10)
            rtt_ms = (time.perf_counter() - inicio) * 1000
            status = resposta.status_code
            erro = ""
        except requests.RequestException as exc:
            rtt_ms = None
            status = ""
            erro = type(exc).__name__

        linhas.append({
            "condicao": condicao,
            "i": i,
            "rtt_ms": round(rtt_ms, 3) if rtt_ms is not None else "",
            "status": status,
            "erro": erro,
        })
        time.sleep(intervalo)

    sessao.close()
    return linhas


def main():
    parser = argparse.ArgumentParser(description="Experimento A: RTT de /api/ping.")
    parser.add_argument("--n", type=int, default=50, help="número de medições (mín. 30)")
    parser.add_argument("--intervalo", type=float, default=0.1, help="pausa entre requisições, em s")
    parser.add_argument("--condicao", default="local", help="rótulo usado no nome do CSV")
    parser.add_argument("--nova-conexao", action="store_true",
                        help="abre uma conexão TCP nova por requisição")
    args = parser.parse_args()

    if args.n < 30:
        parser.error("--n deve ser pelo menos 30")

    print(f"Medindo RTT de {API_BASE_URL}/api/ping ({args.n} requisições)...")
    linhas = medir_rtt(args.n, args.intervalo, args.nova_conexao, args.condicao)

    imprimir_resumo("RTT", [l["rtt_ms"] for l in linhas if l["rtt_ms"] != ""])
    falhas = sum(1 for l in linhas if l["erro"])
    if falhas:
        print(f"Falhas: {falhas}")

    salvar_csv(f"rtt_{args.condicao}.csv", linhas)


if __name__ == "__main__":
    main()
