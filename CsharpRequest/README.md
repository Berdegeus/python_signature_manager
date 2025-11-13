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

Durante o `dotnet run`, o console mostra uma linha como:

```
info: Purchase Requests Service[0]
      Porta reservada para execução: 5087
```

Use esse número (5087 no exemplo) para testar com `curl`:

```bash
curl -s http://127.0.0.1:5087/health
curl -s http://127.0.0.1:5087/requests
```

### Seleção dinâmica de portas

- `PORT`: pode receber `auto` para deixar o SO escolher qualquer porta livre (default) ou um número fixo (ex.: `PORT=6000`).
- `PORT_POOL`: **opcional**; só defina quando quiser limitar o range (formato `5085-5095`). Sem esse valor o serviço usa apenas `PORT`.
- `SERVICE_HOST`: hostname divulgado para o Consul/gateway (default `localhost`).

Exemplo com pool (somente se realmente precisar de um range controlado):

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

Ou utilize o `docker-compose.yml` recém-incluído (publica a porta interna 8080 em `58085` no host e inclui health check):

```bash
cd CsharpRequest
docker compose up --build
# acompanhar logs
docker compose logs -f purchase_requests
# derrubar
docker compose down
```

Veja a porta escolhida no log do container:

```bash
docker compose logs -f purchase_requests | grep "Porta reservada"
# Porta exposta no host (fixa em 58085)
curl http://127.0.0.1:58085/health
```

Exemplo de saída: `Porta reservada para execução: 5089`. Use essa porta com os `curl` de teste.

> **Portas**: localmente o serviço usa `PORT=auto` (dinâmico, exibido no log). No Docker, a porta interna fica fixa em `8080` e é publicada em `58085` no host (`http://127.0.0.1:58085`).

Para várias instâncias, forneça `PORT` diferentes ou um `PORT_POOL` compartilhado e exponha as portas correspondentes (o gateway/generic ingress fará o balanceamento e aceitará os tokens gerados via `jwt_service`).

## Configuração

Todas as configurações possuem equivalente via `appsettings.json` ou variáveis de ambiente:

| Chave | Descrição |
| --- | --- |
| `ConnectionStrings:DefaultConnection` | Arquivo SQLite. |
| `PortPool` / `PORT_POOL` | Intervalo opcional de portas. Deixe vazio para usar apenas `PORT`. |
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
