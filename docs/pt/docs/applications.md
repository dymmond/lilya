# Aplicações

Lilya traz uma classe chamada `Lilya` que encapsula toda a funcionalidade da aplicação.

```python
from lilya.apps import Lilya
```

Existem várias maneiras de criar uma aplicação Lilya, mas:

=== "Resumidamente"

    ```python
    {!> ../../../docs_src/applications/nutshell.py !}
    ```

=== "Com Include"

    ```python
    {!> ../../../docs_src/applications/with_include.py!}
    ```

## Testar usando o curl

```shell
$ curl -X GET http://localhost:8000/user/lilya
```
## Criar uma instância de uma aplicação

Criar uma instância de uma aplicação pode ser feito de diferentes maneiras e com uma grande vantagem de usar as
[configurações](./settings.md) para uma abordagem mais limpa.

**Parâmetros**:

* **debug** - Boolean que indica se deve retornar o *traceback* em caso de erro. Basicamente, modo de *debug*,
muito útil para desenvolvimento.
* **settings_module** - Uma instância ou definição de classe de [configurações](./settings.md) de onde os valores das configurações
serão lidos.
* **routes** - Uma lista de rotas que escutam pedidos HTTP e WebSocket recebidos.
Uma lista de [Path](./routing.md#path), [WebSocketPath](./routing.md#websocketpath), [Include](./routing.md#include) e
[Host](./routing.md#host).
* **permissions** - Uma lista de [permissões](./permissions.md) para atender aos pedidos de escutra da aplicação
(HTTP e WebSockets).
* **middleware** - Uma lista de [middlewares](./middleware.md) para serem executados para cada solicitação. Os middlewares podem ser subclasses do [MiddlewareProtocol](./middleware.md#middlewareprotocol).
* **exception_handlers** - Um dicionário de [tipos de exceção](./exceptions.md) (ou exceções personalizadas) e as
funções num nível superior da aplicação. As funções de exceção devem estar no formato
`handler(request, exc) -> response` e podem ser funções padrão ou funções assíncronas.
* **on_shutdown** - Uma lista de funções para serem executadas no encerramento da aplicação. As funções de encerramento não recebem nenhum
argumento e podem ser funções padrão ou funções assíncronas.
* **on_startup** - Uma lista de funções para serem executadas na inicialização da aplicação. As funções de inicialização não recebem nenhum
argumento e podem ser funções padrão ou funções assíncronas.
* **lifepan** - A função de contexto de vida útil é um estilo mais recente que substitui os *handlers* on_startup / on_shutdown.
Use um ou outro, não ambos.
* **include_in_schema** - Boolean para indicar se deve ser incluído no *schema** ou não. Isso pode ser útil
se estiver a descontinuar uma aplicação Lilya [Incluída](./routing.md#include) inteira em favor de uma nova. O *boolean*
deve indicar que todos os caminhos devem ser considerados obsoletos.
* **redirect_slashes** - Boolean para habilitar/desabilitar redirecionamento de barras para os *handlers*. Está activo por defeito.

## Configurações da aplicação

As configurações são outra forma de controlar os parâmetros passados para o objeto Lilya ao instanciar. Consulte as [configurações](./settings.md) para obter mais detalhes e como usá-las para potencializar sua aplicação.

Para aceder às configurações da aplicação, existem diferentes formas:

=== "Dentro do pedido da aplicação"

    ```python hl_lines="6"
    {!> ../../../docs_src/applications/settings/within_app_request.py!}
    ```

=== "A partir das configurações globais"

    ```python hl_lines="1 6"
    {!> ../../../docs_src/applications/settings/global_settings.py!}
    ```

## Estado e instância da aplicação

Pode armazenar um estado extra arbitrário na instância da aplicação utilizando o atributo `state`.

Exemplo:

```python hl_lines="6"
{!> ../../../docs_src/applications/app_state.py !}
```

## Aceder à instância da aplicação

A instância da aplicação está **sempre** disponível através de `request` ou através de `context`.

**Examplo**

```python
from lilya.apps import Lilya
from lilya.requests import Request
from lilya.context import Context
from lilya.routing import Path


# For request
def home_request(request: Request):
    app = request.app
    return {"message": "Welcome home"}


# For context
def home_context(context: Context):
    app = context.app
    return {"message": "Welcome home"}


app = Lilya(routes=[
        Path("/request", home_request),
        Path("/context", home_context),
    ]
)
```
