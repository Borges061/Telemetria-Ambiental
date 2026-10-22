# Painel de Monitoramento Ambiental

Aplicação distribuída de comunicação e monitoramento em tempo real, desenvolvida como
Projeto 1 da disciplina de Redes de Computadores (2026).

O sistema coleta leituras de múltiplos sensores, transmite os dados a um servidor central,
persiste o histórico, dispara alertas automáticos com base em limiares e apresenta tudo em
um painel web atualizado em tempo real. O projeto inclui ainda uma avaliação experimental
da comunicação em rede e uma análise de segurança do tráfego.

## Visão geral

Sensores simulados geram leituras ambientais (temperatura, umidade e outras métricas) e as
enviam ao servidor por dois canais distintos: WebSocket e UDP. O servidor valida, autentica
e armazena cada leitura, avalia os limiares configurados e repassa as atualizações e os
alertas para os painéis conectados, em tempo real. Operações de consulta, cadastro e
configuração são feitas por HTTP.

```
  [Sensor 1]  --UDP-->  \
  [Sensor 2]  --UDP-->   \                        /--WebSocket--> [Painel Web 1]
  [Sensor 3]  --WS---->   >--->  [ SERVIDOR ]  --<
                         /         |    |          \--WebSocket--> [Painel Web 2]
  [Painel/CLI] --HTTP--> /         |    |
                                   v    v
                              [ SQLite ] [ Logs ]
```

## Principais funcionalidades

- Coleta de leituras por WebSocket e por UDP, com identificação independente de cada
  dispositivo.
- Atualização do painel em tempo real via WebSocket.
- Operações de consulta, cadastro e configuração por HTTP/REST.
- Protocolo de aplicação próprio, documentado em `docs/protocolo.md`.
- Persistência em SQLite com histórico consultável.
- Alertas automáticos baseados em limiares configuráveis.
- Autenticação simples por token de dispositivo e validação de entradas.
- Registro de logs com timestamps e tratamento de desconexões e mensagens inválidas.
- Avaliação experimental de rede (RTT, throughput, concorrência, TCP vs UDP) e análise de
  tráfego com Wireshark.

## Arquitetura

| Componente       | Responsabilidade                                               |
|------------------|----------------------------------------------------------------|
| Servidor         | Recebe leituras (WebSocket e UDP), valida, autentica, persiste, avalia limiares e faz broadcast para os painéis. |
| Sensores         | Geram leituras simuladas e as transmitem ao servidor.          |
| Painel web       | Consome as atualizações em tempo real e exibe leituras, histórico e alertas. |
| Persistência     | Banco SQLite com dispositivos, leituras, alertas e limiares.   |

## Tecnologias

- Servidor: Python 3.11+ com FastAPI e uvicorn (HTTP e WebSocket).
- Banco de dados: SQLite.
- Sensores: Python (WebSocket e sockets UDP).
- Painel: HTML, CSS e JavaScript.
- Experimentos e gráficos: Python, com pandas e matplotlib.
- Análise de tráfego e segurança: Wireshark, tcpdump e mitmproxy.

## Estrutura do repositório

```
projeto-monitoramento/
├── README.md
├── requirements.txt
├── servidor/        Servidor FastAPI: HTTP, WebSocket, protocolo, persistencia e auth
├── sensores/        Sensores simulados (WebSocket e UDP)
├── painel/          Painel web (dashboard em tempo real)
├── experimentos/    Scripts de medicao de rede e geracao de graficos
├── seguranca/       Roteiro da analise de seguranca (capturas nao versionadas)
└── docs/            Especificacao do protocolo e relatorio tecnico
```

## Requisitos

- Python 3.11 ou superior.
- Navegador web moderno.
- Wireshark (para a etapa de análise de tráfego).

## Instalação

```bash
git clone https://github.com/<usuario>/<repositorio>.git
cd <repositorio>
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Execução

Inicie o servidor:

```bash
uvicorn servidor.main:app --host 0.0.0.0 --port 8000
```

Inicie um ou mais sensores, em terminais separados:

```bash
python sensores/sensor_ws.py --device-id sensor-01
python sensores/sensor_udp.py --device-id sensor-02
```

Abra o painel:

```
Abra painel/index.html no navegador, ou sirva a pasta painel/ por HTTP.
```

As instruções detalhadas de cada componente estão nos respectivos diretórios.

## Protocolo de aplicação

O formato das mensagens, a sequência de operações, os códigos de erro e exemplos completos
estão especificados em `docs/protocolo.md`.

## Segurança e privacidade

Este é um repositório público. Não são versionados segredos (tokens, chaves, certificados),
o banco de dados, logs nem capturas de tráfego, conforme definido em `.gitignore`. As
capturas do Wireshark e demais dados sensíveis são mantidos apenas localmente; o relatório
utiliza recortes anonimizados. A demonstração de man-in-the-middle descrita em `seguranca/`
é executada exclusivamente contra a própria aplicação, em ambiente de laboratório
controlado.

## Equipe

| Integrante | Responsabilidade principal                                    |
|------------|---------------------------------------------------------------|
| Pessoa 1   | Servidor, protocolo, persistência e autenticação              |
| Pessoa 2   | Sensores simulados, painel web e alertas                      |
| Pessoa 3   | Experimentos de rede, análise com Wireshark e segurança       |

A tabela de contribuição individual detalhada consta no relatório técnico.

## Licença

Projeto acadêmico desenvolvido para fins educacionais.
