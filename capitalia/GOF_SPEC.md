# Especificação dos Padrões GoF – Serviço Capitalia (Python)

## Padrões Estruturais

### Facade — `RequestProcessor`
* **Motivação:** Fornecer um ponto de entrada único para o servidor HTTP manual acionar todo o fluxo de tratamento de requisições, encapsulando a criação do contexto, a chamada à cadeia de handlers e o pós-processamento de cabeçalhos.
* **Onde está evidenciado:** Classe `RequestProcessor` declarada em `capitalia/app/handlers.py`, com docstring e método `handle` que orquestra o pipeline antes de devolver a resposta final ao servidor.
* **Como foi implementado:** O construtor recebe o handler inicial e o método `handle` instancia `RequestContext`, delega ao elo inicial da cadeia e aplica cabeçalhos transversais como `Access-Control-Allow-Origin` e `Content-Length` antes de retornar ao chamador.

### Adapter — `MySQLUserRepository` e `SqliteUserRepository`
* **Motivação:** Isolar a camada de domínio da tecnologia de persistência, convertendo registros MySQL/SQLite para entidades `User` enquanto cumpre a interface `UserRepository` esperada pelo domínio.
* **Onde está evidenciado:** Porta `UserRepository` em `capitalia/ports/repositories.py` e adaptadores concretos `MySQLUserRepository` e `SqliteUserRepository` em `capitalia/adapters/mysql_repo.py` e `capitalia/adapters/sqlite_repo.py`.
* **Como foi implementado:** Cada adaptador recebe uma conexão específica, executa SQL nativo do respectivo banco, converte o resultado para `User` com auxiliares `_to_entity` e implementa os métodos `get_by_id`, `get_by_email`, `add` e `save`, cumprindo o contrato da porta.

## Padrões Comportamentais

### Strategy — autenticação intercambiável
* **Motivação:** Permitir que o pipeline HTTP valide tokens sem acoplar-se a um mecanismo concreto, habilitando a introdução de novas políticas de autenticação apenas trocando a estratégia injetada.
* **Onde está evidenciado:** Interface abstrata `AuthStrategy` e implementação `JwtAuthStrategy` em `capitalia/app/auth_strategies.py`, utilizadas pelo `AuthHandler` ao montar o pipeline em `capitalia/app/handlers.py`.
* **Como foi implementado:** `AuthStrategy` define o método `authenticate` e `JwtAuthStrategy` injeta o segredo JWT para delegar a verificação ao módulo de infraestrutura. O `AuthHandler` recebe a estratégia no construtor e delega a ela a validação do token Bearer antes de permitir o avanço da requisição.

### Chain of Responsibility — pipeline de handlers HTTP
* **Motivação:** Encadear responsabilidades (log, tratamento de erros, roteamento, autenticação, HEAD, despacho) sem concentrá-las em um único handler rígido, permitindo inserir ou substituir etapas conforme necessário.
* **Onde está evidenciado:** Interface `Handler` e `RequestContext` em `capitalia/app/http.py`, além da hierarquia `AbstractHandler` e handlers concretos (`LoggingHandler`, `ErrorHandler`, `OptionsHandler`, `RoutingHandler`, `AuthHandler`, `HeadHandler`, `DispatchHandler`) definidos em `capitalia/app/handlers.py` e encadeados pela função `build_handler`.
* **Como foi implementado:** `AbstractHandler` mantém referência ao próximo elo e oferece `_handle_next` para delegação. Cada handler concreto implementa `handle` para sua responsabilidade e chama o próximo elo. `build_handler` instancia e liga os handlers na ordem desejada antes de entregar o `RequestProcessor` com o elo inicial.

### State — transições de status de usuário
* **Motivação:** Encapsular regras de transição entre estados de usuário (ativo, suspenso, expirado) e de avaliação de status efetivo, evitando condicionais dispersas no serviço de assinaturas.
* **Onde está evidenciado:** Hierarquia `UserState`, `ActiveState`, `SuspendedState`, `ExpiredState` e o registro `_STATE_REGISTRY` em `capitalia/domain/user_states.py`, consumidos por `SubscriptionService` em `capitalia/domain/services.py`.
* **Como foi implementado:** Cada subclasse de `UserState` sobrescreve apenas as operações válidas para o estado, ajustando o objeto `User` conforme necessário. O serviço resolve o estado atual por meio de `get_user_state`, delega a avaliação e executa transições, persistindo as mudanças através do repositório.
