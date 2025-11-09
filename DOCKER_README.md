# Python Signature Manager - Docker Setup

Este documento explica como executar o projeto Python Signature Manager usando Docker.

## Arquivos Docker

- `services/capitalia/Dockerfile`: Define a imagem do serviço Python "Capitalia"
- `services/router/Dockerfile`: Imagem do proxy HTTP
- `services/purchase_requests/Dockerfile`: Imagem do serviço .NET de solicitações de compra
- `docker-compose.yml`: Orquestra os serviços e volumes compartilhados
- `.dockerignore`: Arquivos ignorados durante o build

## Como usar

### 1. Usando Docker Compose (Recomendado)

```bash
# 1. Clone o repositório e navegue até o diretório
cd python_signature_manager

# 2. (Opcional) Ajuste variáveis de ambiente em um arquivo `.env`
#    As variáveis padrão atendem ao desenvolvimento local.

# 3. Construa e suba os serviços
docker compose up -d --build

# 4. Verifique os logs consolidados
docker compose logs -f

# 5. Para parar a aplicação
docker compose down
```

### 2. Usando Docker diretamente

```bash
# 1. Construir a imagem do serviço Capitalia
docker build -t capitalia-service -f services/capitalia/Dockerfile services/capitalia

# 2. Criar diretório para dados
mkdir -p data

# 3. Executar o container
docker run -d \
  --name capitalia-service \
  -p 8080:8080 \
  -e DB_KIND=sqlite \
  -e SQLITE_PATH=/app/data/capitalia.db \
  -e JWT_SECRET=your-secret-here \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/services/capitalia:/app/services/capitalia \
  -v $(pwd)/libs/python:/app/libs/python:ro \
  capitalia-service

# 4. Verificar logs
docker logs capitalia-service

# 5. Parar o container
docker stop capitalia-service
docker rm capitalia-service
```

## Configurações

### Variáveis de Ambiente

**Capitalia**

- `DB_KIND`: Tipo de banco (`sqlite` ou `mysql`)
- `SQLITE_PATH`: Caminho para o banco SQLite (se usar SQLite)
- `MYSQL_HOST`: Host do MySQL (se usar MySQL)
- `MYSQL_USER`: Usuário do MySQL
- `MYSQL_PASSWORD`: Senha do MySQL
- `MYSQL_DB`: Nome do banco MySQL
- `MYSQL_PORT`: Porta do MySQL
- `JWT_SECRET`: Chave secreta para JWT
- `PORT`: Porta exposta pelo serviço (padrão: 8080)

**Router**

- `BACKEND_HOST`: Host/IP do serviço de backend
- `BACKEND_PORT`: Porta exposta pelo backend
- `ROUTER_PORT`: Porta de escuta do proxy (padrão: 80)

**Purchase Requests**

- `ConnectionStrings__DefaultConnection`: String de conexão do EF Core
- `Consul__Address`: Endpoint do agente Consul (opcional)

### Usando MySQL

Para usar MySQL, descomente as seções correspondentes no `docker-compose.yml` e configure as variáveis de ambiente adequadamente.

## Portas

- Capitalia: `8080`
- Router: `80`
- Purchase Requests: `5000`
- Consul (opcional): `8500`

## Volumes

- `capitalia_data`: Persistência do SQLite do Capitalia (`/app/data`)
- `purchase_requests_data`: Persistência opcional do banco do serviço de compras (`/app/data`)

## Health Check

O container inclui um health check que verifica se a aplicação está respondendo.

## Segurança

- A aplicação executa como usuário não-root (`appuser`)
- Use senhas fortes em produção
- Configure adequadamente as variáveis de ambiente

## Troubleshooting

```bash
# Ver logs detalhados de um serviço específico
docker compose logs -f capitalia

# Executar comandos dentro do container
docker compose exec capitalia bash

# Reconstruir a imagem de um serviço
docker compose build --no-cache capitalia
```
