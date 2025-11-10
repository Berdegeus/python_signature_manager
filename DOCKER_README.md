# Python Signature Manager - Docker Setup

Este documento explica como executar o projeto Python Signature Manager usando Docker.

## Arquivos Docker

- `Dockerfile`: Define a imagem Docker da aplicação
- `docker-compose.yml`: Configuração para execução com Docker Compose
- `.dockerignore`: Arquivos ignorados durante o build
- `.env.example`: Exemplo de configuração de variáveis de ambiente

## Como usar

### 1. Usando Docker Compose (Recomendado)

```bash
# 1. Clone o repositório e navegue até o diretório
cd python_signature_manager

# 2. Copie e configure as variáveis de ambiente
cp .env.example .env
# Edite o arquivo .env com suas configurações

# 3. Execute a aplicação
docker-compose up -d

# 4. Verifique os logs
docker-compose logs -f

# 5. Para parar a aplicação
docker-compose down

# 6. Subir múltiplas instâncias (ex.: 4) compartilhando o range 8000-8100
docker compose up --build --scale app=4 router

> Obs.: o `docker-compose.yml` usa `network_mode: host` para que todos os containers compartilhem o range 8000-8100 e o router publique na porta 80. Este modo está disponível nativamente em Linux. Em macOS/Windows utilize WSL2 ou um host Linux para espelhar o mesmo comportamento.
```

### 2. Usando Docker diretamente

```bash
# 1. Construir a imagem
docker build -t python-signature-manager .

# 2. Criar diretório para dados
mkdir -p data

# 3. Executar o container (Linux) compartilhando a stack de rede para usar o range 8000-8100
docker run -d \
  --name signature-manager \
  --network host \
  -e DB_KIND=sqlite \
  -e SQLITE_PATH=/app/data/capitalia.db \
  -e JWT_SECRET=your-secret-here \
  -e HOST=0.0.0.0 \
  -e PORT=8000-8100 \
  -e PORT_POOL=8000-8100 \
  -v $(pwd)/data:/app/data \
  python-signature-manager

# 4. Verificar logs
docker logs signature-manager

# 5. Parar o container
docker stop signature-manager
docker rm signature-manager

# 6. (Opcional) Construir e executar o roteador na porta 80
docker build -t capitalia-router ./router
docker run -d \
  --name signature-router \
  --network host \
  -e BACKEND_HOST=127.0.0.1 \
  -e BACKEND_PORTS=8000-8100 \
  -e ROUTER_PORT=80 \
  capitalia-router
```

## Configurações

### Variáveis de Ambiente

- `DB_KIND`: Tipo de banco (`sqlite` ou `mysql`)
- `SQLITE_PATH`: Caminho para o banco SQLite (se usar SQLite)
- `MYSQL_HOST`: Host do MySQL (se usar MySQL)
- `MYSQL_USER`: Usuário do MySQL
- `MYSQL_PASSWORD`: Senha do MySQL
- `MYSQL_DB`: Nome do banco MySQL
- `MYSQL_PORT`: Porta do MySQL
- `JWT_SECRET`: Chave secreta para JWT
- `HOST`: Interface/IP para bind (padrão `0.0.0.0`)
- `PORT`: Porta(s) preferenciais. O padrão é `8000-8100`, permitindo que várias instâncias coexistam automaticamente no host.
- `PORT_POOL`: Mesmo formato de `PORT`, mas com prioridade quando definido. Use-o para refletir exatamente o range monitorado pelo router (sem incluir `auto`).
- `BACKEND_HOST`: host que o roteador usará para alcançar o backend (padrão `app`).
- `BACKEND_PORTS`/`BACKEND_PORT_POOL`: lista/intervalos de portas monitoradas pelo roteador. Deve refletir os valores de `PORT`/`PORT_POOL` configurados nas instâncias Capitalia (não inclua `auto`).
- `BACKEND_DISCOVERY_INTERVAL`: intervalo em segundos entre verificações do roteador (default `2`).
- `BACKEND_TIMEOUT`: timeout das chamadas do roteador para o backend (default `10`).

### Usando MySQL

Para usar MySQL, descomente as seções correspondentes no `docker-compose.yml` e configure as variáveis de ambiente adequadamente.

## Portas

- A aplicação escuta `PORT` (ou a primeira porta disponível do `PORT_POOL`). Por padrão, ela ocupa o primeiro slot livre entre `8000` e `8100`.
- O MySQL (se habilitado) é exposto na porta `3306`
- O roteador publica a API unificada em `80`

## Volumes

- `./data:/app/data`: Armazena o banco de dados SQLite

## Health Check

O container inclui um health check que verifica se a aplicação está respondendo.

## Segurança

- A aplicação executa como usuário não-root (`appuser`)
- Use senhas fortes em produção
- Configure adequadamente as variáveis de ambiente

## Troubleshooting

```bash
# Ver logs detalhados
docker-compose logs -f app

# Executar comandos dentro do container
docker-compose exec app bash

# Reconstruir a imagem
docker-compose build --no-cache
```
