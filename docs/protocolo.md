# Protocolo de Aplicação — Telemetria Ambiental

Todas as mensagens são JSON (UTF-8). O campo `tipo` identifica a operação. Timestamps são
ISO 8601 com fuso (ex.: `2026-10-29T16:00:00-03:00`).

## Métricas e limiares

| Métrica        | Unidade | Faixa normal | valor_min | valor_max |
|----------------|---------|--------------|-----------|-----------|
| `temperatura`  | C       | 20–30        | 15        | 35        |
| `umidade`      | %       | 40–70        | 30        | 80        |
| `qualidade_ar` | AQI     | 0–80         | —         | 100       |

Valor fora de `[valor_min, valor_max]` gera alerta (`nivel` do limiar, padrão `critico`).

## Mensagens

### leitura (sensor → servidor, via WebSocket ou UDP)
```json
{"tipo":"leitura","device_id":"sensor-01","token":"abc123",
 "timestamp":"2026-10-29T16:00:00-03:00","metrica":"temperatura",
 "valor":23.7,"unidade":"C","seq":42}
```
`seq` é incremental por sensor e permite detectar perda e reordenação (UDP). Campos extras
(ex.: `padding`) são ignorados pelo servidor.

### update (servidor → painel)
```json
{"tipo":"update","device_id":"sensor-01","metrica":"temperatura",
 "valor":23.7,"unidade":"C","timestamp":"2026-10-29T16:00:00-03:00"}
```

### alerta (servidor → painel)
```json
{"tipo":"alerta","device_id":"sensor-01","metrica":"temperatura","valor":41.2,
 "limiar":35.0,"nivel":"critico","timestamp":"2026-10-29T16:05:00-03:00"}
```

### erro (servidor → cliente)
```json
{"tipo":"erro","codigo":"TOKEN_INVALIDO","mensagem":"Dispositivo não autenticado","seq":42}
```
Por UDP não há canal de resposta: o erro é apenas registrado no log do servidor.

| Código                 | Causa                                              |
|------------------------|----------------------------------------------------|
| `TOKEN_INVALIDO`       | `device_id` desconhecido ou token incorreto        |
| `CAMPO_FALTANDO`       | campo obrigatório ausente                          |
| `VALOR_INVALIDO`       | tipo/valor inválido (ex.: `valor` não numérico)    |
| `METRICA_DESCONHECIDA` | métrica fora de `temperatura/umidade/qualidade_ar` |
| `FORMATO_INVALIDO`     | mensagem não é um objeto JSON válido               |

## Endpoints HTTP (porta 8000)

| Método | Rota                                     | Descrição                                   |
|--------|------------------------------------------|---------------------------------------------|
| POST   | `/api/dispositivos`                      | corpo `{"nome":"..."}` → `{device_id, token}` |
| GET    | `/api/leituras?device=&metrica=&limite=` | histórico (mais recentes primeiro)          |
| GET    | `/api/alertas`                           | lista de alertas                            |
| PUT    | `/api/limiares`                          | `{metrica, valor_min, valor_max, nivel}`    |
| GET    | `/api/status`                            | `{uptime_s, paineis}`                       |
| GET    | `/api/ping`                              | `{pong:true, t_servidor}` (Experimento A)   |

## WebSocket e UDP

- `ws://host:8000/ws/sensor` — sensores enviam `leitura`; recebem `erro` se inválida.
- `ws://host:8000/ws/painel` — painéis recebem `update` e `alerta`.
- `udp://host:9999` — um datagrama = uma `leitura` JSON.

## Sequência típica

1. Sensor: `POST /api/dispositivos` → recebe `device_id` e `token`.
2. Sensor envia `leitura` (WS ou UDP) com `seq` crescente.
3. Servidor valida, autentica, grava, faz broadcast de `update` e, se violar limiar, de `alerta`.
