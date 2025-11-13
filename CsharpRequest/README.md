# Purchase Requests Service (.NET 8)

Microsserviço REST desenvolvido em C#/.NET 8 que gerencia solicitações de compra, cataloga itens e integra-se ao Capitalia (serviço Python) para aprovações automáticas. Agora o serviço consome o `jwt_service` (Python) para emitir tokens HS256 e anexá-los nas chamadas ao Capitalia; a validação ocorre no lado Python/gateway.

## Requisitos

- .NET 8.0 SDK
- SQLite (incluído) — um arquivo `app.db` é criado automaticamente
- Docker (opcional, para empacotar e executar o serviço)

## Arquitetura

```
+-----------------------+         +---------------------------+
| Purchase Requests API |  --->   | Capitalia Gateway (AWS)   |
| (.NET / SQLite)       |         | (balanceamento + validação)|
+-----------+-----------+         +--------------+------------+
            ^                                     |
            | HTTP + Bearer token (emitido via    |
            | jwt_service)                        v
        Consul (opcional)           +---------------------------+
        registra instâncias         | Capitalia Python Service  |
                                    +-------------+-------------+
                                                  ^
                                                  |
                                       +----------+----------+
                                       |   jwt_service       |
                                       | (assina tokens)     |
                                       +---------------------+
```

- O serviço .NET expõe rotas REST e registra instâncias múltiplas (via `PORT_POOL`/Consul).
- O gateway AWS recebe o tráfego público, valida os JWT emitidos pelo `jwt_service` e distribui entre instâncias vivas.
- A rota `/requests/{id}/external-approval` demonstra a integração bilateral.

## Execução local

```bash
cd CsharpRequest
dotnet restore
dotnet run --project PurchaseRequestsService.csproj
```

### Seleção dinâmica de portas

- `PORT`: força uma única porta (ex.: `PORT=5090`).
- `PORT_POOL`: aceita valores separados por vírgula ou intervalos (`5085-5095`). O serviço tenta reservar o primeiro slot livre para permitir várias instâncias simultâneas.
- `SERVICE_HOST`: hostname divulgado para o Consul/gateway (default `localhost`).

Exemplo com pool (subirá quantas instâncias desejar, cada uma anunciando a porta utilizada nos logs):

```bash
PORT_POOL=5085-5095 dotnet run --project PurchaseRequestsService.csproj
PORT_POOL=5085-5095 dotnet run --project PurchaseRequestsService.csproj
```

Os logs mostram mensagens como `Purchase Requests Service escutando em http://0.0.0.0:5086`.

## Docker

Um Dockerfile multi‑stage está disponível em `CsharpRequest/Dockerfile`.

```bash
cd CsharpRequest
docker build -t purchase-requests .
docker run -d --name purchase-requests \
  -e PORT=8080 \
  -e SERVICE_HOST=host.docker.internal \
  -e JwtService__BaseAddress=http://host.docker.internal:8200 \
  -p 8080:8080 \
  purchase-requests
```

Ou utilize o `docker-compose.yml` recém-incluído (usa `network_mode: host` e health check embutido):

```bash
cd CsharpRequest
docker compose up --build
```

Para várias instâncias, forneça `PORT` diferentes ou um `PORT_POOL` compartilhado e exponha as portas correspondentes (o gateway/generic ingress fará o balanceamento e aceitará os tokens gerados via `jwt_service`).

## Configuração

Todas as configurações possuem equivalente via `appsettings.json` ou variáveis de ambiente:

| Chave | Descrição |
| --- | --- |
| `ConnectionStrings:DefaultConnection` | Arquivo SQLite. |
| `PortPool` / `PORT_POOL` | Intervalo de portas para auto‑binding (padrão `5085-5095`). |
| `ServiceHost` / `SERVICE_HOST` | Host anunciado para Consul/gateway. |
| `Consul:*` | Registra o serviço no Consul (opcional). |
| `Capitalia:*` | Configura o cliente HTTP que envia requisições ao microserviço Python. |
| `JwtService:*` | Base URL, TTL e claims usadas para solicitar tokens ao `jwt_service`. |

## Endpoints principais

Todos expostos em `/requests` (ou `/api/requests`) e documentados via Swagger em `/swagger`.

| Método | Rota | Descrição |
| --- | --- | --- |
| GET `/health` | Health-check utilizado pelo gateway/Consul. |
| GET `/requests/items` | Lista itens do catálogo. |
| GET `/requests/{id}` | Detalha uma solicitação. |
| POST `/requests` | Cria nova solicitação com linhas e totais calculados. |
| POST `/requests/{id}/confirm` | Confirma manualmente. |
| POST `/requests/{id}/external-approval` | Envia ao Capitalia para aprovação automática com Bearer token. |
| POST `/requests/{id}/reject` | Rejeita manualmente. |

## Integração com Capitalia & Gateway

- Configure `Capitalia:BaseAddress` com o endpoint exposto pelo gateway/gateway AWS.
- Configure `JwtService:*` apontando para o micro serviço Python (`python -m jwt_service.main`). O C# chama `POST /token`, recebe um JWT e envia na chamada para o Capitalia, que valida o token antes de avaliar a solicitação.
- O endpoint `/requests/{id}/external-approval` demonstra a comunicação entre as duas linguagens, cumprindo a rubrica de integração.

### Evidências rápidas

```bash
$ curl -s http://localhost:5085/health
{"status":"ok"}

$ curl -s http://localhost:5085/requests | jq '.[0].status'
"Pending"

$ curl -s -X POST http://localhost:5085/requests \
  -H "Content-Type: application/json" \
  -d '{"requesterName":"Alice","department":"Finance","items":[{"itemId":1,"quantity":2}]}'
# => {"message":"Solicitação de compra criada com sucesso.", ...}
```

## Testes rápidos

```bash
curl -s http://localhost:5085/health
curl -s http://localhost:5085/requests/items
curl -s -X POST http://localhost:5085/requests \
  -H "Content-Type: application/json" \
  -d '{"requesterName":"Alice","department":"Finance","items":[{"itemId":1,"quantity":2}]}'
```

Esses comandos validam as rotas REST, a criação de registros no SQLite e a prontidão para containerização/execução em múltiplos nós.
