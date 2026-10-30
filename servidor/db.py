"""
persistência de dados do servidor.

gerencia a conexão com o banco SQLite,
cria as tabelas necessárias e realiza operações de
inserção e consulta dos dispositivos, leituras, alertas
e limiares de monitoramento.
"""


import os
import sqlite3
from pathlib import Path

DB_PATH = Path(
    os.getenv(
        "DATABASE_PATH",
        str(Path(__file__).resolve().parent.parent / "monitoramento.db")
    )
)

def conectar():
    conexao = sqlite3.connect(DB_PATH)
    conexao.row_factory = sqlite3.Row
    return conexao


def inicializar_banco():
    with conectar() as conexao:
        conexao.executescript("""
            CREATE TABLE IF NOT EXISTS dispositivos (
                device_id TEXT PRIMARY KEY,
                token TEXT,
                nome TEXT,
                criado_em TEXT
            );

            CREATE TABLE IF NOT EXISTS leituras (
                id INTEGER PRIMARY KEY,
                device_id TEXT,
                metrica TEXT,
                valor REAL,
                unidade TEXT,
                timestamp TEXT,
                seq INTEGER
            );

            CREATE TABLE IF NOT EXISTS alertas (
                id INTEGER PRIMARY KEY,
                device_id TEXT,
                metrica TEXT,
                valor REAL,
                limiar REAL,
                nivel TEXT,
                timestamp TEXT
            );

            CREATE TABLE IF NOT EXISTS limiares (
                metrica TEXT PRIMARY KEY,
                valor_max REAL,
                valor_min REAL,
                nivel TEXT
            );
        """)

def salvar_leitura(device_id, metrica, valor, unidade, timestamp, seq):
    with conectar() as conexao:
        cursor = conexao.execute(
            """
            INSERT INTO leituras
            (device_id, metrica, valor, unidade, timestamp, seq)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (device_id, metrica, valor, unidade, timestamp, seq)
        )
        return cursor.lastrowid


def listar_leituras(device=None, metrica=None, limite=100):
    consulta = "SELECT * FROM leituras WHERE 1=1"
    parametros = []

    if device:
        consulta += " AND device_id = ?"
        parametros.append(device)

    if metrica:
        consulta += " AND metrica = ?"
        parametros.append(metrica)

    consulta += " ORDER BY id DESC LIMIT ?"
    parametros.append(limite)

    with conectar() as conexao:
        registros = conexao.execute(consulta, parametros).fetchall()
        return [dict(registro) for registro in registros]


def salvar_alerta(device_id, metrica, valor, limiar, nivel, timestamp):
    with conectar() as conexao:
        cursor = conexao.execute(
            """
            INSERT INTO alertas
            (device_id, metrica, valor, limiar, nivel, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (device_id, metrica, valor, limiar, nivel, timestamp)
        )
        return cursor.lastrowid


def listar_alertas():
    with conectar() as conexao:
        registros = conexao.execute(
            "SELECT * FROM alertas ORDER BY id DESC"
        ).fetchall()
        return [dict(registro) for registro in registros]


def set_limiar(metrica, valor_max, valor_min, nivel):
    with conectar() as conexao:
        conexao.execute(
            """
            INSERT INTO limiares
            (metrica, valor_max, valor_min, nivel)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(metrica) DO UPDATE SET
                valor_max = excluded.valor_max,
                valor_min = excluded.valor_min,
                nivel = excluded.nivel
            """,
            (metrica, valor_max, valor_min, nivel)
        )


def get_limiar(metrica):
    with conectar() as conexao:
        registro = conexao.execute(
            "SELECT * FROM limiares WHERE metrica = ?",
            (metrica,)
        ).fetchone()

        return dict(registro) if registro else None

def init_db():
    """Inicializa as tabelas do banco de dados."""
    inicializar_banco()

def criar_dispositivo(device_id, token, nome, criado_em):
    """Salva um novo dispositivo no banco de dados."""
    with conectar() as conexao:
        conexao.execute(
            """
            INSERT INTO dispositivos
            (device_id, token, nome, criado_em)
            VALUES (?, ?, ?, ?)
            """,
            (device_id, token, nome, criado_em)
        )

def buscar_dispositivo(device_id):
    """Busca um dispositivo pelo seu identificador."""
    with conectar() as conexao:
        registro = conexao.execute(
            """
            SELECT device_id, token, nome, criado_em
            FROM dispositivos
            WHERE device_id = ?
            """,
            (device_id,)
        ).fetchone()

        return dict(registro) if registro else None