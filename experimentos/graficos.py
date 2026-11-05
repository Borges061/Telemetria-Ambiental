"""
Gera os gráficos (PNG) e uma tabela-resumo (resumo.md) a partir dos CSVs
em resultados/. Cada gráfico só é gerado se o CSV correspondente existir.

Uso:
    python graficos.py
"""

import glob
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from comum import RESULTADOS  # noqa: E402

# Cores por papel (paleta de referência, tema claro). A cor segue a
# entidade: TCP/WebSocket é sempre azul e UDP é sempre laranja.
COR = {
    "tcp": "#2a78d6",
    "ws": "#2a78d6",
    "udp": "#eb6834",
    "neutra": "#2a78d6",
    "referencia": "#52514e",
}
ROTULO = {"tcp": "TCP", "ws": "WebSocket (TCP)", "udp": "UDP"}
ROTULO_CONDICAO = {
    "docker": "Conexão reaproveitada\n(keep-alive)",
    "docker_sem_keepalive": "Conexão nova\npor requisição",
    "base": "Base",
    "atraso_50ms": "+50 ms",
    "atraso_50ms_jitter_10ms": "+50±10 ms",
    "perda_5pct": "5% perda",
    "perda_10pct": "10% perda",
}
TEXTO = "#0b0b0b"
TEXTO_SECUNDARIO = "#52514e"
GRADE = "#e6e5e0"

plt.rcParams.update({
    "figure.dpi": 150,
    "savefig.dpi": 200,
    "font.size": 9,
    "axes.titlesize": 10,
    "axes.labelsize": 9,
    "axes.edgecolor": GRADE,
    "axes.labelcolor": TEXTO_SECUNDARIO,
    "axes.titlecolor": TEXTO,
    "axes.grid": True,
    "axes.grid.axis": "y",
    "axes.axisbelow": True,
    "grid.color": GRADE,
    "grid.linewidth": 0.8,
    "xtick.color": TEXTO_SECUNDARIO,
    "ytick.color": TEXTO_SECUNDARIO,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "legend.frameon": False,
    "lines.linewidth": 2,
})

resumo_md = []


def ler(nome):
    caminho = RESULTADOS / nome
    return pd.read_csv(caminho) if caminho.exists() else None


def salvar(fig, nome):
    fig.tight_layout()
    caminho = RESULTADOS / nome
    fig.savefig(caminho, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Gráfico salvo em {caminho}")


def rotular_barras(ax, barras, formato="{:.0f}", erros=None, vazias=None):
    """
    Escreve o valor acima de cada barra (acima da barra de erro, se houver).
    Em `vazias`, as posições marcadas recebem esse texto no lugar do valor.
    """
    erros = list(erros) if erros is not None else [0] * len(barras)
    vazias = list(vazias) if vazias is not None else [None] * len(barras)
    for barra, erro, vazia in zip(barras, erros, vazias):
        altura = barra.get_height()
        x = barra.get_x() + barra.get_width() / 2
        if vazia:
            # Ancorado na base do eixo (funciona também em escala log).
            ax.annotate(vazia, (x, 0), xycoords=ax.get_xaxis_transform(),
                        xytext=(0, 3), textcoords="offset points",
                        ha="center", va="bottom", fontsize=7, color=TEXTO_SECUNDARIO, rotation=90)
        elif pd.notna(altura):
            topo = altura + (erro if pd.notna(erro) else 0)
            ax.annotate(
                formato.format(altura), (x, topo),
                xytext=(0, 2), textcoords="offset points",
                ha="center", va="bottom", fontsize=7, color=TEXTO_SECUNDARIO,
            )


def eixo_percentual(ax, valores):
    """Eixo de perda começando em 0, com folga para os rótulos."""
    maior = pd.to_numeric(pd.Series(valores), errors="coerce").max()
    ax.set_ylim(0, max(1.0, (maior if pd.notna(maior) else 0) * 1.25))


def boxplot(ax, grupos, rotulos, cor):
    caixa = ax.boxplot(
        grupos, tick_labels=rotulos, patch_artist=True, widths=0.5,
        medianprops={"color": TEXTO, "linewidth": 1.5},
        whiskerprops={"color": TEXTO_SECUNDARIO},
        capprops={"color": TEXTO_SECUNDARIO},
        flierprops={"marker": "o", "markersize": 3, "markerfacecolor": cor,
                    "markeredgecolor": "white", "alpha": 0.7},
    )
    for corpo in caixa["boxes"]:
        corpo.set_facecolor(cor)
        corpo.set_alpha(0.35)
        corpo.set_edgecolor(cor)


def tabela_md(titulo, df):
    colunas = [str(c) for c in df.columns]
    linhas = [
        "| " + " | ".join(colunas) + " |",
        "|" + "|".join("---" for _ in colunas) + "|",
    ]
    for _, linha in df.iterrows():
        valores = ["" if pd.isna(v) else str(v) for v in linha]
        linhas.append("| " + " | ".join(valores) + " |")
    resumo_md.append(f"## {titulo}\n\n" + "\n".join(linhas) + "\n")


def estatisticas(serie):
    serie = pd.to_numeric(serie, errors="coerce").dropna()
    return {
        "n": len(serie),
        "media": round(serie.mean(), 3),
        "mediana": round(serie.median(), 3),
        "desvio": round(serie.std(ddof=0), 3),
        "min": round(serie.min(), 3),
        "max": round(serie.max(), 3),
    }


# ------------------------------------------------------------ Experimento A

def grafico_a():
    arquivos = sorted(glob.glob(str(RESULTADOS / "rtt_*.csv")))
    if not arquivos:
        return
    dfs = [pd.read_csv(a) for a in arquivos]
    rotulos = [df["condicao"].iloc[0] for df in dfs]
    grupos = [pd.to_numeric(df["rtt_ms"], errors="coerce").dropna() for df in dfs]

    fig, ax = plt.subplots(figsize=(max(4, 1.4 * len(dfs) + 2), 3.2))
    boxplot(ax, grupos, [ROTULO_CONDICAO.get(r, r) for r in rotulos], COR["neutra"])
    ax.set_title("Experimento A: RTT de GET /api/ping")
    ax.set_xlabel("Condição")
    ax.set_ylabel("RTT (ms)")
    salvar(fig, "exp_a_rtt.png")

    tabela_md("Experimento A: RTT (ms)", pd.DataFrame(
        [{"condicao": r, **estatisticas(g)} for r, g in zip(rotulos, grupos)]
    ))


# ------------------------------------------------------------ Experimento B

def grafico_b():
    df = ler("throughput.csv")
    if df is None:
        return
    tamanhos = sorted(df["tamanho_bytes"].unique())
    canais = [c for c in ("ws", "udp") if c in set(df["canal"])]
    largura = 0.8 / len(canais)
    posicoes = range(len(tamanhos))

    fig, (ax_vazao, ax_perda) = plt.subplots(1, 2, figsize=(8, 3.2))
    for i, canal in enumerate(canais):
        dados = df[df["canal"] == canal].set_index("tamanho_bytes").reindex(tamanhos)
        # Mensagem que nem saiu do emissor (ex.: datagrama maior que o limite)
        # não é perda na rede: aparece como "não enviado", sem barra.
        nao_enviado = dados["enviadas"] == 0
        vazias = ["não enviado" if v else None for v in nao_enviado]
        kb_s = dados["kb_s"].where(~nao_enviado)
        perda = dados["perda_pct"].where(~nao_enviado)

        x = [p + (i - (len(canais) - 1) / 2) * largura for p in posicoes]
        barras = ax_vazao.bar(x, kb_s, largura * 0.92, color=COR[canal], label=ROTULO[canal])
        rotular_barras(ax_vazao, barras, vazias=vazias)
        barras = ax_perda.bar(x, perda, largura * 0.92, color=COR[canal], label=ROTULO[canal])
        rotular_barras(ax_perda, barras, "{:.1f}", vazias=vazias)

    for ax in (ax_vazao, ax_perda):
        ax.set_xticks(list(posicoes), [formatar_bytes(t) for t in tamanhos])
        ax.set_xlim(-0.6, len(tamanhos) - 0.4)
        ax.set_xlabel("Tamanho da mensagem")
    ax_vazao.set_yscale("log")
    ax_vazao.set_title("Vazão entregue ao painel")
    ax_vazao.set_ylabel("Vazão (KB/s, escala log)")
    ax_perda.set_title("Mensagens enviadas e não entregues")
    ax_perda.set_ylabel("Perda (%)")
    eixo_percentual(ax_perda, df.loc[df["enviadas"] > 0, "perda_pct"])
    ax_vazao.legend(loc="upper left")
    salvar(fig, "exp_b_throughput.png")

    tabela_md("Experimento B: vazão por tamanho", df)


def formatar_bytes(n):
    if n >= 1000:
        return f"{n / 1000:g} KB"
    return f"{n} B"


# ------------------------------------------------------------ Experimento C

def grafico_c():
    for arquivo in sorted(glob.glob(str(RESULTADOS / "concorrencia_*.csv"))):
        if arquivo.endswith("_amostras.csv"):
            continue
        canal = Path(arquivo).stem.split("_")[1]
        df = pd.read_csv(arquivo)
        amostras = ler(f"concorrencia_{canal}_amostras.csv")
        clientes = list(df["clientes"])

        fig, (ax_taxa, ax_atraso) = plt.subplots(1, 2, figsize=(8, 3.2))
        posicoes = range(len(clientes))
        barras = ax_taxa.bar(posicoes, df["msgs_s"], 0.5, color=COR[canal], label="Entregue ao painel")
        rotular_barras(ax_taxa, barras)
        ax_taxa.plot(posicoes, df["taxa_oferecida_msgs_s"], color=COR["referencia"],
                     linestyle="--", marker="o", markersize=5, linewidth=1.5, label="Oferecida pelos clientes")
        ax_taxa.set_xticks(list(posicoes), [str(c) for c in clientes])
        ax_taxa.set_title("Taxa total de mensagens")
        ax_taxa.set_xlabel("Clientes simultâneos")
        ax_taxa.set_ylabel("Mensagens por segundo")
        ax_taxa.legend()

        if amostras is not None:
            grupos = [amostras[amostras["clientes"] == c]["atraso_painel_ms"] for c in clientes]
            boxplot(ax_atraso, grupos, [str(c) for c in clientes], COR[canal])
        ax_atraso.set_title("Atraso sensor até painel")
        ax_atraso.set_xlabel("Clientes simultâneos")
        ax_atraso.set_ylabel("Atraso (ms)")
        fig.suptitle(f"Experimento C: concorrência ({ROTULO[canal]})", fontsize=10, color=TEXTO)
        salvar(fig, f"exp_c_concorrencia_{canal}.png")

        tabela_md(f"Experimento C: concorrência ({ROTULO[canal]})", df)


# ------------------------------------------------------------ Experimento D

def grafico_d():
    for arquivo in sorted(glob.glob(str(RESULTADOS / "tcp_udp_*.csv"))):
        condicao = Path(arquivo).stem.removeprefix("tcp_udp_")
        df = pd.read_csv(arquivo)
        agrupado = (
            df.groupby(["proto", "tamanho_bytes"])
            .agg(mbit_s=("mbit_s", "mean"), mbit_s_desvio=("mbit_s", lambda s: s.std(ddof=0)),
                 perda_pct=("perda_pct", "mean"), fora_ordem=("fora_ordem", "mean"))
            .reset_index()
        )
        tamanhos = sorted(agrupado["tamanho_bytes"].unique())
        posicoes = range(len(tamanhos))
        largura = 0.4

        fig, (ax_vazao, ax_perda) = plt.subplots(1, 2, figsize=(8, 3.2))
        for i, proto in enumerate(("tcp", "udp")):
            dados = agrupado[agrupado["proto"] == proto].set_index("tamanho_bytes").reindex(tamanhos)
            x = [p + (i - 0.5) * largura for p in posicoes]
            # Barra de erro assimétrica: a parte de baixo não passa de zero.
            erro = [dados["mbit_s_desvio"].clip(upper=dados["mbit_s"]), dados["mbit_s_desvio"]]
            barras = ax_vazao.bar(x, dados["mbit_s"], largura * 0.92, yerr=erro,
                                  color=COR[proto], label=ROTULO[proto],
                                  error_kw={"ecolor": TEXTO_SECUNDARIO, "elinewidth": 1, "capsize": 2})
            rotular_barras(ax_vazao, barras, "{:.1f}", erros=dados["mbit_s_desvio"])
            barras = ax_perda.bar(x, dados["perda_pct"], largura * 0.92, color=COR[proto], label=ROTULO[proto])
            rotular_barras(ax_perda, barras, "{:.2f}")

        eixo_percentual(ax_perda, agrupado["perda_pct"])
        for ax in (ax_vazao, ax_perda):
            ax.set_xticks(list(posicoes), [formatar_bytes(t) for t in tamanhos])
            ax.set_xlabel("Tamanho da mensagem")
        ax_vazao.set_title("Vazão (média das repetições)")
        ax_vazao.set_ylabel("Vazão (Mbit/s)")
        ax_perda.set_title("Mensagens perdidas")
        ax_perda.set_ylabel("Perda (%)")
        ax_vazao.legend()
        fig.suptitle(f"Experimento D: TCP vs UDP ({condicao})", fontsize=10, color=TEXTO)
        salvar(fig, f"exp_d_tcp_udp_{condicao}.png")

        tabela_md(f"Experimento D: TCP vs UDP ({condicao}, média das repetições)", agrupado.round(3))


# ------------------------------------------------------------ Experimento E

def grafico_e():
    rtt = ler("condicoes_rtt.csv")
    udp = ler("condicoes_udp.csv")
    if rtt is None and udp is None:
        return

    fig, (ax_rtt, ax_udp) = plt.subplots(1, 2, figsize=(9, 3.4))
    if rtt is not None:
        condicoes = list(dict.fromkeys(rtt["condicao"]))
        grupos = [pd.to_numeric(rtt[rtt["condicao"] == c]["rtt_ms"], errors="coerce").dropna() for c in condicoes]
        boxplot(ax_rtt, grupos, [ROTULO_CONDICAO.get(c, c) for c in condicoes], COR["tcp"])
        # Escala log: os picos de retransmissão (centenas de ms) não achatam as caixas.
        ax_rtt.set_yscale("log")
        tabela_md("Experimento E: RTT por condição (ms)", pd.DataFrame(
            [{"condicao": c, **estatisticas(g)} for c, g in zip(condicoes, grupos)]
        ))
    ax_rtt.set_title("RTT de /api/ping (TCP)")
    ax_rtt.set_xlabel("Condição")
    ax_rtt.set_ylabel("RTT (ms, escala log)")

    if udp is not None:
        barras = ax_udp.bar(range(len(udp)), udp["perda_pct"], 0.5, color=COR["udp"])
        rotular_barras(ax_udp, barras, "{:.1f}")
        ax_udp.set_xticks(range(len(udp)), [ROTULO_CONDICAO.get(c, c) for c in udp["condicao"]])
        eixo_percentual(ax_udp, udp["perda_pct"])
        tabela_md("Experimento E: entrega UDP por condição", udp)
    ax_udp.set_title("Leituras UDP não entregues")
    ax_udp.set_xlabel("Condição")
    ax_udp.set_ylabel("Perda (%)")
    fig.suptitle("Experimento E: condições de rede com tc netem", fontsize=10, color=TEXTO)
    salvar(fig, "exp_e_condicoes.png")


def main():
    for gerar in (grafico_a, grafico_b, grafico_c, grafico_d, grafico_e):
        gerar()

    if resumo_md:
        caminho = RESULTADOS / "resumo.md"
        caminho.write_text("# Resumo dos experimentos\n\n" + "\n".join(resumo_md), encoding="utf-8")
        print(f"Resumo salvo em {caminho}")
    else:
        print(f"Nenhum CSV encontrado em {RESULTADOS}")


if __name__ == "__main__":
    main()
