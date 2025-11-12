# JWT Service

Micro serviço HTTP responsável por assinar JSON Web Tokens (HS256) para o ecossistema Capitalia. Ele roda 100% sobre a biblioteca
padrão do Python (sem frameworks) e pode ser reutilizado por quaisquer outros consumidores que compartilhem o mesmo segredo.

## Requisitos

- Python 3.10+
- Mesmas dependências instaladas para o Capitalia (`pip install -r capitalia/requirements.txt`)

## Executando localmente

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r capitalia/requirements.txt

export JWT_SECRET=troque-por-uma-chave-forte
export JWT_SERVICE_HOST=127.0.0.1  # 0.0.0.0 para aceitar conexões externas
export JWT_SERVICE_PORT=8200
export JWT_DEFAULT_TTL=3600        # opcional, 1 hora por padrão
python -m jwt_service.main
```

O processo imprime uma linha semelhante a `[jwt-service] listening on 127.0.0.1:8200` quando estiver pronto. Use `Ctrl+C` para encerra
r.

## Variáveis de Ambiente

| Variável | Descrição | Default |
| --- | --- | --- |
| `JWT_SECRET` | Segredo compartilhado utilizado para assinar/verificar os tokens | `change-me` |
| `JWT_SERVICE_HOST` | Interface/IP de bind do servidor HTTP | `0.0.0.0` |
| `JWT_SERVICE_PORT` | Porta de escuta do servidor HTTP | `8200` |
| `JWT_DEFAULT_TTL` | Tempo (s) padrão de expiração quando o cliente não informa `ttl` | `3600` |

> O mesmo valor de `JWT_SECRET` deve ser configurado nos serviços consumidores (por exemplo `capitalia`) para que a validação func
ione.

## API HTTP

| Método | Rota | Descrição | Corpo | Resposta |
| --- | --- | --- | --- | --- |
| `GET` | `/health` | Health-check simples | — | `{ "status": "ok" }` |
| `POST` | `/token` | Assina um novo token | `{ "claims": { ... }, "ttl": 3600 }` | `{ "token": "<jwt>" }` |

- `claims` é obrigatório e deve ser um objeto JSON (será serializado diretamente nas claims do JWT).
- `ttl` é opcional; quando omitido o serviço utiliza `JWT_DEFAULT_TTL`.
- Respostas de erro seguem o formato `{ "error": "mensagem" }` com códigos `4xx` ou `5xx`.

## Exemplos com `curl`

```bash
# Health-check
curl -s http://127.0.0.1:8200/health

# Solicitar token
curl -s -X POST http://127.0.0.1:8200/token \
  -H 'Content-Type: application/json' \
  -d '{"claims": {"sub": "1", "email": "alice@example.com"}, "ttl": 900}'
```

## Uso com Docker Compose

O arquivo `docker-compose.yml` na raiz do repositório já declara o serviço `jwt-service`. Para executá-lo junto com o Capitalia e o roteador:

```bash
docker compose up --build
```

Para subir apenas o emissor de tokens:

```bash
docker compose up jwt-service
```

## Integração com outros serviços

Os consumidores devem realizar chamadas HTTP `POST /token` apontando para `JWT_SERVICE_URL` com o mesmo segredo HS256. No Capitalia, configure:

```bash
export JWT_SECRET=troque-por-uma-chave-forte  # igual ao serviço de tokens
export JWT_SERVICE_URL=http://127.0.0.1:8200
export JWT_SERVICE_TIMEOUT=5
```

Com isso, a rota `/login` do Capitalia requisitará tokens ao micro serviço automaticamente.
