# Capitalia — Microsserviço de Assinaturas (HTTP puro)

Microsserviço de streaming construído 100% sobre a biblioteca padrão do Python (sem frameworks web). A solução completa inclui:

- Serviço principal em `capitalia/` (HTTP puro + Ports & Adapters) que agora consome um emissor de JWT externo.
- Router em `router/` para descoberta e balanceamento entre múltiplas instâncias.
- Serviço .NET de solicitações de compra em `CsharpRequest/` (opcional).

## Índice
- [Visão Geral](#visão-geral)
- [Arquitetura](#arquitetura)
- [Requisitos](#requisitos)
- [Guia Rápido (SQLite)](#guia-rápido-sqlite)
- [Alternar para MySQL](#alternar-para-mysql)
- [Variáveis de Ambiente](#variáveis-de-ambiente)
- [Endpoints e Fluxos](#endpoints-e-fluxos)
- [Router & Balanceamento](#router--balanceamento)
- [Diagramas](#diagramas)
- [Testes](#testes)

## Visão Geral

- HTTP Handlers manuais com `BaseHTTPRequestHandler`, CORS básico e suporte a `HEAD`.
- Domínio separado com Repository + Data Mapper, Unit of Work e Strategy para alternar SQLite/MySQL.
- JWT HS256 assinado/verificado manualmente (sem dependências externas).
- Roteador auxiliar faz round-robin entre instâncias (auto-descobertas via `/health`).

## Arquitetura

| Camada | Função |
| --- | --- |
| `capitalia/app/handlers.py` | Recebe requests, valida auth e delega para os casos de uso. |
| `capitalia/domain/*` | Modelos, regras de status/planos e serviço de assinatura. |
| `capitalia/adapters/*` | Repositórios concretos para SQLite/MySQL. |
| `capitalia/ports/*` | Interfaces (clock, repos) e contratos de infra. |
| `router/` | Proxy HTTP simples para distribuir tráfego entre instâncias Capitalia. |

## Requisitos

- Python 3.10+
- SQLite (builtin) ou MySQL 8.x com `PyMySQL`
- `pip` atualizado (para instalar `capitalia/requirements.txt`)

## Guia Rápido (SQLite)

1. Criar virtualenv e instalar deps:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r capitalia/requirements.txt
   ```
2. Provisionar banco:
   ```bash
   python -m capitalia.scripts.init_sqlite
   python -m capitalia.scripts.seed_sqlite
   ```
3. Em um novo terminal, iniciar o micro serviço de autenticação JWT (explicado em [Serviço de Autenticação JWT](#serviço-de-autenticação-jwt)):
   ```bash
   source .venv/bin/activate
   export JWT_SECRET=troque-por-uma-chave-forte
   export JWT_SERVICE_HOST=127.0.0.1
   export JWT_SERVICE_PORT=8200
   python -m jwt_service.main
   ```
   > O serviço imprime `[jwt-service] listening on ...` quando estiver pronto.

4. Em outro terminal, rodar o serviço Capitalia (porta padrão 8000, com fallback automático até 8100):
   ```bash
   source .venv/bin/activate
   export JWT_SECRET=troque-por-uma-chave-forte  # deve ser o mesmo utilizado no micro serviço
   export JWT_SERVICE_URL=http://127.0.0.1:8200
   python -m capitalia.main
   ```
5. Use os comandos `curl` da seção [Endpoints e Fluxos](#endpoints-e-fluxos) para validar o login e as rotas protegidas.

## Alternar para MySQL

1. Configure as variáveis (veja `capitalia/.env.example`):
   ```bash
   export DB_KIND=mysql
   export MYSQL_HOST=localhost
   export MYSQL_USER=capitalia_user
   export MYSQL_PASSWORD=senha
   export MYSQL_DB=capitalia
   export JWT_SECRET=troque-por-uma-chave-forte
   export PORT=8000-8100
   ```
2. Instale dependências e aplique DDL/seed:
   ```bash
   pip install -r capitalia/requirements.txt
   mysql < capitalia/scripts/init_mysql.sql
   mysql < capitalia/scripts/seed_mysql.sql
   python -m capitalia.main
   ```

## Variáveis de Ambiente

| Variável | Descrição | Default |
| --- | --- | --- |
| `HOST` | Interface/IP para bind | `0.0.0.0` |
| `PORT` | Porta única ou intervalo (ex.: `8000-8100`) | `8000-8100` |
| `PORT_POOL` | Mesma sintaxe de `PORT`; use para pools monitorados pelo router | `8000-8100` |
| `DB_KIND` | `sqlite` ou `mysql` | `sqlite` |
| `SQLITE_PATH` | Caminho do `.db` | `capitalia.db` |
| `MYSQL_*` | Host, usuário, senha, banco, porta | vide `.env.example` |
| `JWT_SECRET` | Segredo HS256 compartilhado com o micro serviço | obrigatório |
| `JWT_SERVICE_URL` | URL base do emissor de token externo | `http://127.0.0.1:8200` |
| `JWT_SERVICE_TIMEOUT` | Timeout (s) para chamadas ao emissor externo | `5` |

> `PORT`/`PORT_POOL` aceitam o token `auto` (porta 0) para cenários locais fora do roteador. Quando há router, mantenha ranges explícitos para coincidir com o que ele monitora.

## Endpoints e Fluxos

| Método | Rota | Descrição | Auth |
| --- | --- | --- | --- |
| POST | `/login` | Retorna JWT para usuários válidos | Pública |
| GET | `/user/{id}/status` | Calcula status efetivo (expira trial) | Bearer (`sub == id`) |
| POST | `/user/{id}/upgrade` | `basic|trial → premium` | Bearer |
| POST | `/user/{id}/downgrade` | `premium → basic` | Bearer |
| POST | `/user/{id}/suspend` | Suspende premium | Bearer |
| POST | `/user/{id}/reactivate` | Reativa premium suspenso | Bearer |
| GET | `/health` | `{status:"ok"}` | Pública |

Todos os retornos são JSON, CORS com `Access-Control-Allow-Origin: *`, e `OPTIONS` responde preflight com `Allow`/`Access-Control-Allow-*`.

### Exemplos `curl`

```bash
# Router (porta 80) ou instância direta (ex.: http://localhost:8000)
BASE=${BASE:-http://localhost}

curl -s -X POST "$BASE/login" \
  -H 'Content-Type: application/json' \
  -d '{"email":"alice@example.com","password":"password123"}'

TOKEN="$(curl -s -X POST "$BASE/login" \
  -H 'Content-Type: application/json' \
  -d '{"email":"alice@example.com","password":"password123"}' | jq -r .token)"

curl -s "$BASE/user/1/status" -H "Authorization: Bearer $TOKEN"
curl -s "$BASE/health"
curl -s -X POST "$BASE/user/1/upgrade" -H "Authorization: Bearer $TOKEN"
curl -s -X POST "$BASE/user/1/downgrade" -H "Authorization: Bearer $TOKEN"
curl -s -X POST "$BASE/user/1/suspend" -H "Authorization: Bearer $TOKEN"
curl -s -X POST "$BASE/user/1/reactivate" -H "Authorization: Bearer $TOKEN"
```

### Códigos comuns

- `200 OK` — sucesso.
- `401 Unauthorized` — token ausente/inválido (ou login errado).
- `403 Forbidden` — tentativa de acessar outro `{id}`.
- `404 Not Found` — usuário inexistente.
- `405 Method Not Allowed` — método fora da rota.
- `422 Unprocessable Entity` — payload inválido ou regra de negócio violada.
- `500 Internal Server Error` — erro inesperado (sem stack trace).

## Router & Balanceamento

O diretório `router/` implementa um reverse proxy minimalista:

- Faz round-robin entre portas configuradas (`BACKEND_PORTS`/`BACKEND_PORT_POOL`).
- Verifica saúde via `GET /health`.
- Publica a API unificada na porta `ROUTER_PORT` (default 80).
- Compatível com múltiplas instâncias rodando a partir do mesmo repositório (ex.: `PORT_POOL=8000-8100`).

Exemplo (Linux) com host networking:

```bash
docker compose up --build --scale app=4 router
```

> Em macOS/Windows utilize WSL2 ou rode os processos diretamente fora de containers para simular o mesmo range de portas.

## Serviço de Autenticação JWT

O diretório `jwt_service/` contém um micro serviço independente responsável por assinar tokens HS256. Ele expõe dois endpoints:

| Método | Rota | Descrição |
| --- | --- | --- |
| `GET` | `/health` | Retorna `{ "status": "ok" }` para verificação de saúde |
| `POST` | `/token` | Recebe `{ "claims": { ... }, "ttl": 3600 }` e devolve `{ "token": "..." }` |

### Executar localmente

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r capitalia/requirements.txt  # dependências compartilhadas

export JWT_SECRET=troque-por-uma-chave-forte
export JWT_SERVICE_HOST=127.0.0.1  # ou 0.0.0.0 para aceitar conexões externas
export JWT_SERVICE_PORT=8200
python -m jwt_service.main
```

Variáveis opcionais:

| Variável | Função | Default |
| --- | --- | --- |
| `JWT_DEFAULT_TTL` | Tempo (s) padrão de expiração dos tokens | `3600` |

Enquanto o serviço estiver ativo, o Capitalia solicitará tokens através de `JWT_SERVICE_URL`. Certifique-se de que `JWT_SECRET` seja idêntico nos dois processos.

### Via Docker Compose

```bash
docker compose up jwt-service
```

O arquivo `docker-compose.yml` já inclui o serviço `jwt-service` com as mesmas variáveis de ambiente mostradas acima. Use `docker compose up` (sem filtros) para subir Capitalia, roteador e emissor JWT simultaneamente.

## Diagramas

```
     +---------------------+         +----------------------+
     |  HTTP Handlers      |  uses   |  Domain Services     |
     |  (BaseHTTPRequest)  +--------->  (Use Cases)         |
     +---------------------+         +----------+-----------+
                 |                              |
                 | via UnitOfWork               | Entities/Rules
                 v                              v
        +--------+---------+            +------+-------+
        |   Ports (Repo)   |<-----------+  Domain     |
        |  UoW, Clock      |            |  Models     |
        +---+----------+---+            +--------------+
            ^          ^
            |          |
   +--------+--+   +---+---------+
   | SQLite   |   |   MySQL      |
   | Adapter  |   |   Adapter    |
   +----------+   +--------------+
```

```
Client -> POST /login {email,password}
Server: valida credenciais -> assina JWT HS256 (exp=3600s) -> {token}
Client -> chama rotas com Authorization: Bearer <token>
Server: valida assinatura/exp -> executa caso de uso
```

## Testes

```bash
python -m unittest discover -s tests -p 'test_*.py'
```

## Checklist das Rubricas (deploy AWS)

- **Rubrica 1 — rotas REST + Docker**: `services/capitalia/Dockerfile`, `CsharpRequest/Dockerfile` e `docker-compose.yml` sobem todos os microsserviços com health checks (`/health`). Para validar localmente execute `docker compose up --build` e use os `curl` de exemplo em cada README.
- **Rubrica 2 — integração entre linguagens com JWT e balanceamento**: suba `jwt_service`, `capitalia`, `router` e múltiplas instâncias do `CsharpRequest` (via `PORT_POOL`). Chame `POST /requests/{id}/external-approval`; o serviço .NET busca um token no `jwt_service`, envia para o Capitalia (Python) via gateway/router e recebe a decisão.

Esses mesmos passos são os que serão executados no ambiente AWS (gateway fornecido separadamente).

Os testes de integração (`tests/test_http_flow_sqlite.py`, etc.) exercitam o handler completo, garantindo regressão mínima ao alterar regras ou mensagens.

### POST /user/{id}/upgrade
- Autenticação: `Bearer`.
- Autorização: somente o próprio usuário (`sub == {id}`).
- Ação: `basic|trial → premium` e `status=active`.
- Corpo: vazio.
- Sucesso 200: `{ "user_id": <id>, "plan": "premium", "status": "active" }`.
- Erros:
  - 401 Unauthorized: token ausente/inválido/expirado.
  - 403 Forbidden: outro `{id}`.
  - 404 Not Found: usuário inexistente.
  - 422 Unprocessable Entity: plano atual não permite upgrade (já é premium).
  - 500 Internal Server Error.

### POST /user/{id}/downgrade
- Autenticação: `Bearer`.
- Autorização: somente o próprio usuário (`sub == {id}`).
- Ação: `premium → basic` e `status=active`.
- Corpo: vazio.
- Sucesso 200: `{ "user_id": <id>, "plan": "basic", "status": "active" }`.
- Erros:
  - 401 Unauthorized; 403 Forbidden; 404 Not Found.
  - 422 Unprocessable Entity: não está em premium.
  - 500 Internal Server Error.

### POST /user/{id}/suspend
- Autenticação: `Bearer`.
- Autorização: somente o próprio usuário (`sub == {id}`).
- Ação: suspende somente se `plan=premium`.
- Corpo: vazio.
- Sucesso 200: `{ "user_id": <id>, "plan": "premium", "status": "suspended" }`.
- Erros:
  - 401 Unauthorized; 403 Forbidden; 404 Not Found.
  - 422 Unprocessable Entity: não está em premium.
  - 500 Internal Server Error.

### POST /user/{id}/reactivate
- Autenticação: `Bearer`.
- Autorização: somente o próprio usuário (`sub == {id}`).
- Ação: reativa somente se `plan=premium` e `status=suspended`.
- Corpo: vazio.
- Sucesso 200: `{ "user_id": <id>, "plan": "premium", "status": "active" }`.
- Erros:
  - 401 Unauthorized; 403 Forbidden; 404 Not Found.
  - 422 Unprocessable Entity: não está suspenso/premium.
  - 500 Internal Server Error.

### Autenticação e JWT
- Header: `Authorization: Bearer <token>`.
- Assinatura: HS256; payload inclui `sub` (id do usuário), `email`, `plan`, `iat`, `exp`.
- Expiração padrão: 3600s (1h).

### Códigos de erro (resumo)
- 200 OK: operação bem-sucedida.
- 401 Unauthorized: token ausente/inválido/expirado (ou login inválido).
- 403 Forbidden: usuário tentando acessar/modificar outro `{id}`.
- 404 Not Found: recurso inexistente (ex.: usuário).
- 405 Method Not Allowed: método HTTP incorreto para a rota (ex.: usar GET onde é POST).
- 422 Unprocessable Entity: JSON inválido/campos obrigatórios ausentes ou regra de negócio violada.
- 500 Internal Server Error: erro inesperado; mensagem genérica (sem stack trace).

## AWS RDS (MySQL) — Passo a passo

1) Criar instância RDS MySQL

- Console AWS → RDS → Create database → MySQL 8.x
- Template: Free tier (se disponível)
- DB instance identifier: `capitalia-mysql`
- Defina master username/password
- VPC default
- Public access: Yes (apenas para TDE; produção: Private + bastion)
- Security Group: permita Inbound TCP 3306 somente do seu IP
- Crie e aguarde status `Available`

2) Obter endpoint

- Em Databases → selecione a instância → copie Endpoint e Port (3306)

3) Criar database lógico e usuário

```sql
mysql -h <ENDPOINT> -P 3306 -u <MASTER_USER> -p
CREATE DATABASE capitalia CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE USER 'capitalia_user'@'%' IDENTIFIED BY '<senha-forte>';
GRANT ALL PRIVILEGES ON capitalia.* TO 'capitalia_user'@'%';
FLUSH PRIVILEGES;
```

4) Aplicar DDL e seed

- Rode `capitalia/scripts/init_mysql.sql` e `capitalia/scripts/seed_mysql.sql` no DB `capitalia`.

5) Configurar o microsserviço

```bash
export DB_KIND=mysql
export MYSQL_HOST=<endpoint RDS>
export MYSQL_USER=capitalia_user
export MYSQL_PASSWORD=<senha>
export MYSQL_DB=capitalia
export JWT_SECRET=<segredo forte>
pip install -r capitalia/requirements.txt
python capitalia/main.py
```

## Testes

Execute:

```bash
python -m unittest discover -s tests -p 'test_*.py'
```
