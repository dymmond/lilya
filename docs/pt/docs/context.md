# Contexto

O `Context` é um objecto único para o **Lilya**. O `context` é um parâmetro que pode ser usado **dentro dos *handlers*** e fornece informações adicionais que pode precisar por qualquer motivo específico.

A abordagem é muito parecida ao [Request](./requests.md) em termos de implementação, mas não é a mesma coise.
Na realidade, um `context` contém também o 'request' e informações sobre o próprio *handler*.

Importar é tão simples como:

```python
from lilya.context import Context
```

## A classe `Context`

Pode-se considerar o `context` como o `contexto do pedido` de um determinado *handler*.
Isto também significa que, quando um *handler* (visualização) é declarado, todas as informações passadas para ele estão automaticamente acessíveis por meio do parâmetro
`context.handler`.

```python
{!> ../../../docs_src/context/app.py !}
```

O `context` também fornece o acesso ao objecto [`request`](./requests.md), bem como às configurações da applicação e outras funções.

Isso significa que, se desejar passar um `request` e um `context`, na realidade só precisa do `context`, pois o pedido já está disponível internamente,
mas mesmo assim, se desejar, pode passar ambos.

**Example**

```python
from lilya.apps import Lilya
from lilya.context import Context
from lilya.routing import Path


def read_context(context: Context, id: str):
    host = context.request.client.host

    context_data = context.get_context_data()
    context.add_to_context("name", "Lilya")

    context_data = context.get_context_data()
    context_data.update({
        "host": host, "user_id": id
    })
    return context_data


app = Lilya(
    routes=[
        Path("/users/{id}", read_request)
    ]
)
```

O `contexto` torna-se especialmente útil quando precisa de aceder a informações do `handler` que não estão disponíveis após a instanciação do mesmo.
Por exemplo, é útil quando se acede à `context.settings` para obter as configurações da aplicação, oferecendo uma abordagem versátil para as aceder.

## Atributos

### Handler

A função *handler* que é responsável pelo pedido.

```python
from lilya.context import Context
from lilya.responses import Response


def home(context: Context):
    handler = context.handler

    return Response("Ok")
```

### Pedido

O pedido a ser usado no âmbito do *handler*.

```python
from lilya.context import Context
from lilya.responses import Response


def home(context: Context):
    request = context.request

    return Response("Ok")
```

### Utilizador

O utilizador alocado ao pedido.

```python
from lilya.context import Context
from lilya.responses import Response


def home(context: Context):
    user = context.user

    return Response("Ok")
```

### Utilizador

O utilizador alocado ao pedido.

```python
from lilya.context import Context
from lilya.responses import Response


def home(context: Context):
    user = context.user

    return Response("Ok")
```

### Configurações

As [configurações](./settings.md) sendo usadas pela aplicação Lilya.

Podem ser as configurações globais ou se um `settings_module` foi fornecido, retorna essas mesmas configurações.

```python
from lilya.context import Context
from lilya.responses import Response


def home(context: Context):
    settings = context.settings

    return Response("Ok")
```

### Âmbito

O âmbito do *handler* da aplicação.

```python
from lilya.context import Context
from lilya.responses import Response


def home(context: Context):
    scope = context.scope

    return Response("Ok")
```

### Aplicação

A aplicação Lilya.

```python
from lilya.context import Context
from lilya.responses import Response


def home(context: Context):
    app = context.app

    return Response("Ok")
```

## Métodos

O `context` também fornece diferentes funções para manipular o objecto.

### get_context_data

# Contexto

O contexto da aplicação. Pode ser especialmente útil ao trabalhar com templates.

```python
from lilya.context import Context
from lilya.responses import Response


def home(context: Context):
    context = context.get_context_data()

    return Response("Ok")
```

### add_to_context

Adiciona valores ao contexto atual.

```python
from lilya.context import Context
from lilya.responses import Response


def home(context: Context):
    context.add_to_context("call", "ok")

    return Response("Ok")
```

### url_path_for

Obtém o caminho de um *handler* específico.

```python
from lilya.context import Context
from lilya.responses import Response


def home(context: Context):
    url = context.url_path_for("/home")

    return Response(url)
```
