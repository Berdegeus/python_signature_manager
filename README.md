# Capitalia — Microsserviço de Gestão de Assinaturas (HTTP puro)

Microsserviço único para gestão de assinaturas de streaming construído sem frameworks web, aproveitando HTTP puro, JWT manual, Ports & Adapters, Repository + Data Mapper, Unit of Work e Strategy para alternar dinamicamente entre SQLite e MySQL (sem ORM).

> **Onde o código vive:** `services/capitalia` contém o serviço Python, `libs/python/*` guarda utilitários compartilhados e os demais serviços (router, purchase_requests, auth, etc.) ficam em `services/`.

## Índice
- [Visão Geral](#visão-geral)
- [Arquitetura e Padrões](#arquitetura-e-padrões)
- [Requisitos](#requisitos)
- [Guia Rápido (SQLite)](#guia-rápido-sqlite)
- [Alternando para MySQL](#alternando-para-mysql)
- [Variáveis de Ambiente](#variáveis-de-ambiente)
- [Endpoints Principais](#endpoints-principais)
- [Fluxos via curl](#fluxos-via-curl)
- [Autenticação & Erros](#autenticação--erros)
- [Diagrama e Fluxo JWT](#diagrama-e-fluxo-jwt)
- [Deploy em AWS RDS](#deploy-em-aws-rds-mysql)
- [Testes](#testes)

## Visão Geral

- Serviço responsável por login, upgrade/downgrade de planos, suspensão e reativação.
- Engine de regras expira trials automaticamente e mantém consistência via Unit of Work.
- API exposta em HTTP puro (`BaseHTTPRequestHandler`) com CORS básico habilitado.
- JWT HS256 assinado manualmente e validado sem dependências externas.

## Arquitetura e Padrões

| Camada | Responsabilidade |
| --- | --- |
| HTTP Handlers | Tradução request/response + roteamento mínimo. |
| Domínio (Use Cases) | Regras de negócio, validações e transições de estado. |
| Ports & Repositórios | Abstração de banco, clocks, gateways e Unit of Work. |
| Adapters | Implementações concretas para SQLite/MySQL compartilhando interface. |

Suporte adicional:
- Strategy para escolher o adapter de banco com `DB_KIND`.
- Repository + Data Mapper para isolar SQL do domínio.
- Unit of Work centraliza commits/rollbacks de forma explícita.

## Requisitos

- Python 3.10+
- SQLite (builtin) ou MySQL 8.x (via `PyMySQL`)
- `pip` atualizado para instalar o pacote em modo editable

## Guia Rápido (SQLite)

1. **Preparar o ambiente virtual**
   ```bash
   # na raiz do repositório
   python scripts/bootstrap_service_env.py capitalia
   cd services/capitalia
   ```
   - macOS/Linux: `source .venv/bin/activate`
   - Windows PowerShell: `.venv\Scripts\Activate.ps1`
   - Windows CMD: `.venv\Scripts\activate.bat`
   - Git Bash (Windows): `source .venv/Scripts/activate`

   > Problemas com o virtualenv? Rode `python scripts/bootstrap_service_env.py capitalia --force` para recriar.

2. **Criar e popular o banco SQLite**
   ```bash
   python -m services.capitalia.scripts.init_sqlite
   python -m services.capitalia.scripts.seed_sqlite
   ```

3. **Subir o serviço (porta padrão 8080)**
   ```bash
   python -m services.capitalia.main
   ```

4. **Autenticar e consumir as rotas protegidas**
   - Use os comandos `curl` da seção [Fluxos via curl](#fluxos-via-curl) para validar rapidamente.

## Alternando para MySQL

1. **Variáveis de ambiente**
   ```bash
   export DB_KIND=mysql
   export MYSQL_HOST=localhost
   export MYSQL_USER=capitalia_user
   export MYSQL_PASSWORD=senha
   export MYSQL_DB=capitalia
   export JWT_SECRET=troque-por-uma-chave-forte
   export PORT=8080
   ```
   > Há um modelo completo em `services/capitalia/.env.example`.

2. **Dependências e migrações**
   ```bash
   pip install -e .
   pip install PyMySQL
   mysql -u <user> -p < scripts/capitalia/init_mysql.sql
   mysql -u <user> -p < scripts/capitalia/seed_mysql.sql
   python -m services.capitalia.main
   ```

3. **Verificar conectividade**
   - Teste `mysql -h <host> -P 3306 -u capitalia_user -p`.
   - Garanta que o security group/liberação da porta 3306 esteja configurado.

## Variáveis de Ambiente

| Variável | Descrição | Default |
| --- | --- | --- |
| `PORT` | Porta HTTP do serviço | `8080` |
| `DB_KIND` | `sqlite` ou `mysql` | `sqlite` |
| `SQLITE_PATH` | Caminho para o arquivo `.db` | `capitalia.db` na raiz do serviço |
| `MYSQL_HOST` / `MYSQL_USER` / `MYSQL_PASSWORD` / `MYSQL_DB` | Configurações MySQL | _obrigatórios quando `DB_KIND=mysql`_ |
| `JWT_SECRET` | Segredo HS256 para assinar tokens | **obrigatório** |
| `JWT_EXP_SECONDS` | TTL do token | `3600` |

> Consulte `services/capitalia/.env.example` para a lista completa.

## Endpoints Principais

| Método | Rota | Descrição | Autenticação |
| --- | --- | --- | --- |
| POST | `/login` | Retorna JWT para o usuário seed ou credenciais válidas | Pública |
| GET | `/user/{id}/status` | Calcula status efetivo, expira trials e persiste mudanças | `Bearer` (sub == id) |
| POST | `/user/{id}/upgrade` | `basic|trial → premium` e mantém `status=active` | `Bearer` |
| POST | `/user/{id}/downgrade` | `premium → basic` preservando `status=active` | `Bearer` |
| POST | `/user/{id}/suspend` | Suspende somente usuários `premium` | `Bearer` |
| POST | `/user/{id}/reactivate` | Reativa premium suspenso | `Bearer` |
| GET | `/health` | Retorna `{status:"ok"}` | Pública |

Todos os retornos são JSON e possuem CORS básico (`Access-Control-Allow-Origin: *`). Requests `OPTIONS` recebem `Allow`, `Access-Control-Allow-Headers` e `Access-Control-Allow-Methods`.

## Fluxos via curl

```bash
# Login (usuário seed)
curl -s -X POST http://localhost:8080/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"alice@example.com","password":"password123"}'

# Guardar token
TOKEN="$(curl -s -X POST http://localhost:8080/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"alice@example.com","password":"password123"}' | jq -r .token)"

# Status efetivo (expira trial)
curl -s http://localhost:8080/user/1/status -H "Authorization: Bearer $TOKEN"

# Healthcheck
curl -s http://localhost:8080/health

# Upgrade/Downgrade
curl -s -X POST http://localhost:8080/user/1/upgrade -H "Authorization: Bearer $TOKEN"
curl -s -X POST http://localhost:8080/user/1/downgrade -H "Authorization: Bearer $TOKEN"

# Suspender / Reativar
curl -s -X POST http://localhost:8080/user/1/suspend -H "Authorization: Bearer $TOKEN"
curl -s -X POST http://localhost:8080/user/1/reactivate -H "Authorization: Bearer $TOKEN"
```

## Autenticação & Erros

- **JWT**: assinatura HS256, payload inclui `sub` (id), `email`, `plan`, `iat`, `exp`. Expiração padrão de 3600s.
- **Headers**: sempre envie `Authorization: Bearer <token>` nas rotas protegidas.
- **Códigos de status**:
  - `200 OK` — operação bem-sucedida.
  - `401 Unauthorized` — token ausente/inválido/expirado ou login inválido.
  - `403 Forbidden` — tentativa de acessar outro `{id}`.
  - `404 Not Found` — usuário ou recurso inexistente.
  - `405 Method Not Allowed` — método não suportado.
  - `422 Unprocessable Entity` — payload inválido ou regra de negócio violada.
  - `500 Internal Server Error` — erro inesperado (sem stack trace).

## Diagrama e Fluxo JWT

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
Server: valida credenciais -> assina JWT HS256 com exp=+3600s -> {token}
Client -> requests protegidas com Authorization: Bearer <token>
Server: verifica assinatura e exp -> autoriza -> executa caso de uso
```

## Deploy em AWS RDS (MySQL)

1. **Criar instância**
   - AWS Console → RDS → Create database → MySQL 8.x.
   - Template *Free tier* (quando disponível).
   - Nome sugerido: `capitalia-mysql`, VPC default, Public access `Yes` apenas para desenvolvimento.
   - Security Group com inbound 3306 liberado somente para seu IP.

2. **Obter endpoint**
   - Em *Databases*, selecione a instância e copie `Endpoint` e porta 3306.

3. **Criar database lógico e usuário**
   ```sql
   mysql -h <ENDPOINT> -P 3306 -u <MASTER_USER> -p
   CREATE DATABASE capitalia CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
   CREATE USER 'capitalia_user'@'%' IDENTIFIED BY '<senha-forte>';
   GRANT ALL PRIVILEGES ON capitalia.* TO 'capitalia_user'@'%';
   FLUSH PRIVILEGES;
   ```

4. **Aplicar DDL/seed**
   - Rode `services/capitalia/scripts/init_mysql.sql` e `services/capitalia/scripts/seed_mysql.sql`.

5. **Configurar o serviço**
   ```bash
   export DB_KIND=mysql
   export MYSQL_HOST=<endpoint RDS>
   export MYSQL_USER=capitalia_user
   export MYSQL_PASSWORD=<senha>
   export MYSQL_DB=capitalia
   export JWT_SECRET=<segredo forte>
   pip install -e services/capitalia
   pip install PyMySQL
   python -m services.capitalia.main
   ```

## Testes

```bash
python -m unittest discover -s tests -p 'test_*.py'
```
