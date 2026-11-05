"""
Experimento D: microteste TCP vs UDP com sockets puros.

Envia a mesma carga (N mensagens de S bytes, mesma taxa) por TCP e por
UDP e compara vazão, perda e ordem. Cada mensagem carrega um `seq`
(4 bytes) no início; o receptor usa o `seq` para contar perdas,
duplicatas e mensagens fora de ordem.

Há um canal de controle TCP (porta 5000) por onde o emissor avisa o
receptor do teste e recebe o resultado. Dados TCP vão na porta 5001
(com prefixo de tamanho de 4 bytes) e dados UDP na porta 5002.

Uso (emissor e receptor no mesmo processo, loopback):
    python exp_d_tcp_udp.py

Uso (receptor em outra máquina/container, ex. para aplicar tc netem):
    python exp_d_tcp_udp.py --modo receptor
    python exp_d_tcp_udp.py --modo emissor --host <ip-do-receptor>
"""

import argparse
import json
import select
import socket
import struct
import threading
import time

from comum import salvar_csv

PORTA_CONTROLE = 5000
PORTA_TCP = 5001
PORTA_UDP = 5002


def _ler_exato(conn, n):
    dados = b""
    while len(dados) < n:
        parte = conn.recv(n - len(dados))
        if not parte:
            return None
        dados += parte
    return dados


def _contar(seqs):
    """Conta recebidas, únicas, duplicadas e fora de ordem."""
    vistos = set()
    duplicadas = 0
    fora_ordem = 0
    maior = -1
    for seq in seqs:
        if seq in vistos:
            duplicadas += 1
            continue
        vistos.add(seq)
        if seq < maior:
            fora_ordem += 1
        maior = max(maior, seq)
    return len(vistos), duplicadas, fora_ordem


# ---------------------------------------------------------------- receptor

def receptor(host="0.0.0.0", parar=None):
    controle = socket.create_server((host, PORTA_CONTROLE), reuse_port=False)
    dados_tcp = socket.create_server((host, PORTA_TCP))
    dados_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dados_udp.bind((host, PORTA_UDP))
    controle.settimeout(0.5)
    print(f"Receptor escutando em {host} (controle {PORTA_CONTROLE}, TCP {PORTA_TCP}, UDP {PORTA_UDP})")

    try:
        while parar is None or not parar.is_set():
            try:
                conn, _ = controle.accept()
            except socket.timeout:
                continue
            with conn:
                arquivo = conn.makefile("rwb")
                linha = arquivo.readline()
                if not linha:
                    continue
                teste = json.loads(linha)
                if teste["proto"] == "tcp":
                    resultado = _receber_tcp(dados_tcp, arquivo)
                else:
                    resultado = _receber_udp(dados_udp, conn, arquivo)
                arquivo.write((json.dumps(resultado) + "\n").encode())
                arquivo.flush()
    finally:
        controle.close()
        dados_tcp.close()
        dados_udp.close()


def _receber_tcp(servidor, arquivo):
    arquivo.write(b"pronto\n")
    arquivo.flush()
    conn, _ = servidor.accept()
    seqs = []
    primeiro = ultimo = None
    with conn:
        while True:
            cabecalho = _ler_exato(conn, 4)
            if cabecalho is None:
                break
            (tamanho,) = struct.unpack("!I", cabecalho)
            corpo = _ler_exato(conn, tamanho)
            if corpo is None:
                break
            agora = time.perf_counter()
            primeiro = primeiro or agora
            ultimo = agora
            seqs.append(struct.unpack("!I", corpo[:4])[0])
    return _resultado(seqs, primeiro, ultimo)


def _receber_udp(sock, conn, arquivo):
    # Descarta datagramas atrasados de um teste anterior.
    sock.setblocking(False)
    while True:
        try:
            sock.recvfrom(65535)
        except BlockingIOError:
            break

    arquivo.write(b"pronto\n")
    arquivo.flush()

    seqs = []
    primeiro = ultimo = None
    fim_pedido = None
    while True:
        espera = 0.5 if fim_pedido is None else max(0.0, fim_pedido + 1.0 - time.perf_counter())
        prontos, _, _ = select.select([sock, conn], [], [], espera)
        if sock in prontos:
            while True:
                try:
                    dados, _ = sock.recvfrom(65535)
                except BlockingIOError:
                    break
                agora = time.perf_counter()
                primeiro = primeiro or agora
                ultimo = agora
                seqs.append(struct.unpack("!I", dados[:4])[0])
        if conn in prontos and fim_pedido is None:
            arquivo.readline()  # "fim"
            fim_pedido = time.perf_counter()
        # Depois do "fim", espera 1 s por datagramas ainda em trânsito.
        if fim_pedido is not None and time.perf_counter() >= fim_pedido + 1.0:
            break
    return _resultado(seqs, primeiro, ultimo)


def _resultado(seqs, primeiro, ultimo):
    unicas, duplicadas, fora_ordem = _contar(seqs)
    return {
        "recebidas": unicas,
        "duplicadas": duplicadas,
        "fora_ordem": fora_ordem,
        "duracao_s": (ultimo - primeiro) if primeiro and ultimo else 0.0,
    }


# ----------------------------------------------------------------- emissor

def _payload(seq, tamanho):
    return struct.pack("!I", seq) + b"x" * max(0, tamanho - 4)


def _pacing(inicio, i, taxa):
    if taxa:
        alvo = inicio + i / taxa
        espera = alvo - time.perf_counter()
        if espera > 0:
            time.sleep(espera)


def testar(host, proto, n, tamanho, taxa):
    with socket.create_connection((host, PORTA_CONTROLE), timeout=30) as controle:
        arquivo = controle.makefile("rwb")
        arquivo.write((json.dumps({"proto": proto, "n": n, "tamanho": tamanho}) + "\n").encode())
        arquivo.flush()
        arquivo.readline()  # "pronto"

        erro = ""
        enviadas = 0
        inicio = time.perf_counter()
        if proto == "tcp":
            with socket.create_connection((host, PORTA_TCP)) as dados:
                for i in range(n):
                    _pacing(inicio, i, taxa)
                    corpo = _payload(i, tamanho)
                    dados.sendall(struct.pack("!I", len(corpo)) + corpo)
                    enviadas += 1
        else:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as dados:
                for i in range(n):
                    _pacing(inicio, i, taxa)
                    try:
                        dados.sendto(_payload(i, tamanho), (host, PORTA_UDP))
                        enviadas += 1
                    except OSError as exc:
                        erro = f"{type(exc).__name__}: {exc.strerror or exc}"
                        break
            arquivo.write(b"fim\n")
            arquivo.flush()
        duracao_envio = time.perf_counter() - inicio

        resultado = json.loads(arquivo.readline())

    recebidas = resultado["recebidas"]
    duracao = resultado["duracao_s"]
    return {
        "proto": proto,
        "tamanho_bytes": tamanho,
        "taxa_alvo_msgs_s": taxa or "max",
        "enviadas": enviadas,
        "recebidas": recebidas,
        "perdidas": enviadas - recebidas,
        "perda_pct": round(100 * (enviadas - recebidas) / enviadas, 3) if enviadas else 100.0,
        "fora_ordem": resultado["fora_ordem"],
        "duplicadas": resultado["duplicadas"],
        "duracao_envio_s": round(duracao_envio, 4),
        "duracao_recepcao_s": round(duracao, 4),
        "msgs_s": round(recebidas / duracao, 1) if duracao else 0.0,
        "mbit_s": round(recebidas * tamanho * 8 / 1e6 / duracao, 3) if duracao else 0.0,
        "erro": erro,
    }


def emissor(args):
    linhas = []
    for tamanho in args.tamanhos:
        for rep in range(1, args.repeticoes + 1):
            for proto in ("tcp", "udp"):
                linha = testar(args.host, proto, args.n, tamanho, args.taxa)
                linha = {"condicao": args.condicao, "rep": rep, **linha}
                print(
                    f"{proto.upper()} {tamanho} B rep {rep}: "
                    f"{linha['recebidas']}/{linha['enviadas']} "
                    f"perda={linha['perda_pct']}% fora_ordem={linha['fora_ordem']} "
                    f"vazão={linha['mbit_s']} Mbit/s {linha['erro']}"
                )
                linhas.append(linha)
                time.sleep(0.5)
    salvar_csv(f"tcp_udp_{args.condicao}.csv", linhas)


def main():
    parser = argparse.ArgumentParser(description="Experimento D: TCP vs UDP com sockets puros.")
    parser.add_argument("--modo", choices=["local", "receptor", "emissor"], default="local")
    parser.add_argument("--host", default="127.0.0.1", help="endereço do receptor (modo emissor)")
    parser.add_argument("--n", type=int, default=5000, help="mensagens por teste")
    parser.add_argument("--tamanhos", default="64,512,1400", help="tamanhos em bytes, separados por vírgula")
    parser.add_argument("--taxa", type=float, default=0, help="mensagens/s (0 = o mais rápido possível)")
    parser.add_argument("--repeticoes", type=int, default=3)
    parser.add_argument("--condicao", default="local", help="rótulo usado no nome do CSV")
    args = parser.parse_args()
    args.tamanhos = [int(t) for t in args.tamanhos.split(",")]
    if any(t < 4 for t in args.tamanhos):
        parser.error("cada tamanho precisa ter pelo menos 4 bytes (o seq)")

    if args.modo == "receptor":
        receptor()
        return

    if args.modo == "local":
        parar = threading.Event()
        thread = threading.Thread(target=receptor, args=("127.0.0.1", parar), daemon=True)
        thread.start()
        time.sleep(0.5)
        args.host = "127.0.0.1"
        try:
            emissor(args)
        finally:
            parar.set()
        return

    emissor(args)


if __name__ == "__main__":
    main()
