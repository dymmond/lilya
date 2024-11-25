# Responses

O Lilya por defeito, fornece *responses* específicas que servem um propósito duplo.
Elas oferecem utilidade e são responsáveis por enviar as mensagens ASGI apropriadas através do canal `send`.

Lilya inclui automaticamente os cabeçalhos `Content-Length` e `Content-Type`.

## Como funciona

Existem algumas formas de usar as respostas numa aplicação Lylia.

* Pode [importar o response](#importando-a-classe-apropriada) apropriada e usá-la diretamente.
* Pode [construir a resposta](#construindo-a-resposta).
* Pode [delegar para o Lilya](#delegando-para-lilya).
* [Construir um codificador personalizado](#construir-um-codificador-personalizado) que permitirá que Lilya analise automaticamente a resposta.

## Respostas disponíveis

Todas as respostas do Lilya herdam do objecto `Response` e essa mesma classe também pode ser usada diretamente.

Todas as respostas são consideradas aplicações ASGI, o que significa que pode tratá-las como tal na sua aplicação, se necessário.

**Exemplo**

```python
from lilya.responses import PlaiText
from lilya.types import Scope, Receive, Send


async def asgi_app(scope: Scope, receive: Receive, send: Send):
    assert scope['type'] == 'http'
    response = PlaiText('Welcome')
    await response(scope, receive, send)
```


### Response

```python
from lilya.responses import Response
```

**Exemplo**

```python
{!> ../../../docs_src/responses/response.py !}
```

##### Definir cookie

Lilya fornece o `set_cookie` que permite definir um cookie numa determinada resposta. Todas as respostas
disponíveis no Lilya têm acesso a essa funcionalidade.

```python
from lilya.responses import Response
from lilya.types import Scope, Receive, Send


async def asgi_app(scope: Scope, receive: Receive, send: Send):
    assert scope['type'] == 'http'
    response = Response('Welcome', media_type='text/plain')

    response.set_cookie(key=..., value=..., max_age=..., expires=...,)
    await response(scope, receive, send)
```

###### Parâmetros

Os parâmetros disponíveis do `set_cookie` são os seguintes:

- `key` - Uma string que representa a chave da cookie.
- `value` - Uma string que representa o valor da cookie.
- `max_age` - Um número inteiro que define o tempo de vida útil da cookie em segundos.
Um valor negativo ou 0 descarta a cookie imediatamente. *(Opcional)*
- `expires` - Um número inteiro que indica os segundos até que a cookie expire ou um objecto datetime. *(Opcional)*
- `path` - Uma string a especificar o subconjunto de rotas a que a cookie se aplica. *(Opcional)*
- `domain` - Uma string a especificar o domínio válido para a cookie. *(Opcional)*
- `secure` - Um booleano que indica que a cookie é enviada para o servidor apenas se o pedido
usa SSL e o protocolo HTTPS. *(Opcional)*
- `httponly` - Um booleano que indica que a cookie não é acessível via JavaScript por meio de Document.cookie,
XMLHttpRequest ou APIs de pedido. *(Opcional)*
- `samesite` - Uma string a especificar a estratégia samesite para a cookie, com valores válidos de `'lax'`, `'strict'` e `'none'`.
Padrão é 'lax'. *(Opcional)*

##### Excluir cookie

Da mesma forma que o [definir cookie](#definir-cookie), esta função está disponível em todas as respostas fornecidas pelo
Lilya.

```python
from lilya.responses import Response
from lilya.types import Scope, Receive, Send


async def asgi_app(scope: Scope, receive: Receive, send: Send):
    assert scope['type'] == 'http'
    response = Response('Welcome', media_type='text/plain')

    response.delete_cookie(key=..., path=..., domain=...)
    await response(scope, receive, send)
```

###### Parâmetros

Os parâmetros disponíveis do `set_cookie` são os seguintes:

- `key` - Uma string que representa a chave da cookie.
- `path` - Uma string a especificar o subconjunto de rotas a que a cookie se aplica. *(Opcional)*
- `domain` - Uma string a especificar o domínio válido para a cookie. *(Opcional)*

### HTMLResponse

Retorna uma resposta `html`.

```python
from lilya.responses import HTMLResponse
```

**Exemplo**

```python
{!> ../../../docs_src/responses/html.py !}
```

### Error

Resposta que pode ser usada ao lançar um erro `500`. Padrão é retornar uma resposta `html`.

```python
from lilya.responses import Error
```

**Exemplo**

```python
{!> ../../../docs_src/responses/error.py !}
```

### PlainText

Resposta que pode ser usada para retornar `text/plain`.

```python
from lilya.responses import PlainText
```

**Exemplo**

```python
{!> ../../../docs_src/responses/plain.py !}
```

### JSONResponse

Resposta que pode ser usada para retornar `application/json`.

```python
from lilya.responses import JSONResponse
```

**Exemplo**

```python
{!> ../../../docs_src/responses/json.py !}
```

### Ok

Resposta que pode ser usada para retornar `application/json` também. Pode ver isto como uma
alternativa ao `JSONResponse`.

```python
from lilya.responses import Ok
```

**Exemplo**

```python
{!> ../../../docs_src/responses/ok.py !}
```

### RedirectResponse

Usado para redirecionar as respostas.

```python
from lilya.responses import RedirectResponse
```

**Exemplo**

```python
{!> ../../../docs_src/responses/redirect.py !}
```

### StreamingResponse

```python
from lilya.responses import StreamingResponse
```

**Exemplo**

```python
{!> ../../../docs_src/responses/streaming.py !}
```

### FileResponse

```python
from lilya.responses import FileResponse
```

Envia um ficheiro de forma assíncrona como resposta, empregando um conjunto distinto de argumentos para a instância em comparação com outros tipos de resposta:

- `path` - O caminho do ficheiro a ser transmitido.
- `status_code` - O código de status a ser retornado.
- `headers` - Cabeçalhos personalizados a serem incluídos, fornecidos como um dicionário.
- `media_type` - Uma string a especificar o tipo de mídia. Se não especificado, o nome do ficheiro ou caminho é usado para deduzir o tipo de mídia.
- `filename` - Se especificado, incluído no Content-Disposition da resposta.
- `content_disposition_type` - Incluído no Content-Disposition da resposta. Pode ser definido como `attachment` (padrão) ou `inline`.
- `background` - Uma instância de [tarefa](./tasks.md).

**Exemplo**

```python
{!> ../../../docs_src/responses/file.py !}
```

## Importando a classe apropriada

Esta é a forma clássica mais usada de usar as respostas. As [respostas disponíveis](#respostas-disponíveis)
contêm uma lista de respostas disponíveis no Lilya, mas também é livre para criar as suas próprias e usá-las.

**Exemplo**

```python
{!> ../../../docs_src/responses/json.py !}
```

## Construir a resposta

Aqui é onde as coisas ficam ótimas. O Lilya fornece uma função `make_response` que automaticamente
construirá a resposta.

```python
from lilya.responses import make_response
```

**Exemplo**

```python
{!> ../../../docs_src/responses/make.py !}
```

Por defeito, o `make_response` retorna um [JSONResponse](#jsonresponse), mas isso também pode ser
alterado se o parâmetro `response_class` for definido como outra coisa.

Então, por que é que o `make_response` é diferente das outras respostas? Bem, aqui é onde Lilya brilha.

O Lilya é puramente Python, o que significa que não depende de bibliotecas externas como Pydantic,
msgspec, attrs ou qualquer outra **mas permite** que se [construa um codificador personalizado](#construir-um-codificador-personalizado) que
pode ser usado posteriormente para serializar a resposta automaticamente e depois passá-la para o `make_response`.

Verifique a secção [construir um codificador personalizado](#construir-um-codificador-personalizado) e [codificadores personalizados com make_response](#codificadores-personalizados-e-o-make_response)
para mais detalhes e como aproveitar o poder do Lilya.

## Delegar para Lilya

Delegar para Lilya significa que, se nenhuma resposta for especificada, Lilya passará pelos
`codificadores` internos e tentará `jsonificar` a resposta.

Vejamos um exemplo.

```python
{!> ../../../docs_src/responses/delegate.py !}
```

Como pode ver, nenhuma `resposta` foi especificada, mas em vez disso, um dicionário Python foi retornado. O que Lilya
faz internamente é *adivinhar* e entender o tipo de resposta, analisar o resultado em `json`
e retornar automaticamente um `JSONResponse`.

Se o tipo de resposta não for serializável em json, então um `ValueError` é lançado.

Vejamos mais alguns exemplos.

```python
{!> ../../../docs_src/responses/delegate_examples.py !}
```

E a lista continua. O Lilya, por design, entende quase todas as estruturas de dados do Python
por defeito, incluindo `Enum`, `deque`, `dataclasses`, `PurePath`, `generators` e `tuple`.

### Codificadores padrão

Para entender como serializar um objecto específico em `json`, o Lilya possui alguns codificadores padrão que são avaliados quando tenta *adivinhar* o tipo de resposta.

* `DataclassEncoder` - Serializa objectos `dataclass`.
* `EnumEncoder` - Serializa objectos `Enum`.
* `PurePathEncoder` - Serializa objectos `PurePath`.
* `PrimitiveEncoder` - Serializa tipos primitivos do Python. `str, int, float e None`.
* `DictEncoder` - Serializa tipos `dict`.
* `StructureEncoder` - Serializa tipos de dados mais complexos. `list, set, frozenset, GeneratorType, tuple, deque`.

E quando um novo codificador é necessário e não é suportado nativamente pelo Lilya? Bem, [construir um codificador personalizado](#construir-um-codificador-personalizado)
é extremamente fácil e possível.

## Construir um codificador personalizado

Como mencionado antes, o Lilya possui [codificadores padrão](#codificadores-padrão) que são usados para transformar uma resposta
numa resposta serializável em `json`.

Para criar um codificador personalizado, deve usar a classe `Encoder` do Lilya e substituir a função `serialize()`
onde ocorre o processo de serialização do tipo de codificador.

Em seguida, **deve registrar o codificador** para que o Lilya o possa usar.

Ao definir um codificador, o `__type__` ou `def is_type(self, value: Any) -> bool:`
**deve ser declarado ou substituído**.

Quando o `__type__` é declarado corretamente, o `is_type` padrão avaliará o objecto em relação ao
tipo e retornará `True` ou `False`.

Isto é usado internamente para perceber o tipo de codificador que será aplicado a um determinado objecto.

!!! warning
    Se não puder fornecer o `__type__` por qualquer motivo e quiser apenas substituir a
    avaliação padrão, simplesmente substitua o `is_type()` e aplique sua lógica personalizada lá.

    Por exemplo: No Python 3.8, para um modelo Pydantic `BaseModel` se passado no `__type__`, ele lançará um
    erro devido a questões internas do Pydantic, então, para contornar esse problema, pode simplesmente substituir o `is_type()`
    e aplicar a lógica que valida o tipo do objecto e retorna um booleano.

```python
from lilya.encoders import Encoder, register_encoder
```

**Exemplo**

Criar e registrar um codificador que lida com tipos `msgspec.Struct`.

```python
{!> ../../../docs_src/encoders/example.py !}
```

Simples, certo? Porque agora o `MsgSpecEncoder` está registrado, pode simplesmente fazer isto nos handlers
e retornar **diretamente** o tipo de objecto `msgspec.Struct`.

```python
from msgspec import Struct

from lilya.routing import Path


class User(Struct):
    name: str
    email: str


def msgspec_struct():
    return User(name="lilya", url="example@lilya.dev")
```

### Criar codificadores personalizados específicos

**Lilya sendo 100% Python puro e não vinculado a nenhuma biblioteca de validação específica** permite que
crie codificadores personalizados que são posteriormente usados pelas respostas do Lilya.

Ok, isso parece um bocado confuso, certo? Aposto que sim, então vamos devagar.

Imagine que quer usar uma biblioteca de validação específica, como [Pydantic](https://pydantic.dev/),
[msgspec](https://jcristharif.com/msgspec/) ou até mesmo [attrs](https://www.attrs.org/en/stable/) ou qualquer outra
à sua escolha.

Quer ter certeza de que, se retornar um modelo Pydantic ou uma msgspec Struct ou até mesmo uma classe `define` attr.

Vejamos como seria para cada um deles.

**Para Pydantic BaseModel**

```python
{!> ../../../docs_src/encoders/pydantic.py !}
```

**Para msgspec Struct**

```python
{!> ../../../docs_src/encoders/example.py !}
```

**Para attrs**

```python
{!> ../../../docs_src/encoders/attrs.py !}
```

Fácil e poderoso, certo? Sim.

Entende o que isso significa? Significa que pode criar **qualquer codificador** à sua escolha usando
também qualquer biblioteca à escolha.

A flexibilidade do Lilya permite que seja livre e para que o Lilya não esteja vinculado a nenhuma biblioteca específica.

#### Codificadores personalizados e respostas

Depois que os [codificadores personalizados nos exemplos](#construir-um-codificador-personalizado) forem criados, isto permite fazer algo diretamente assim.

```python
{!> ../../../docs_src/encoders/responses.py !}
```

#### Codificadores personalizados e o `make_response`

Bem, aqui é onde o `make_response` o ajuda. O `make_response` irá gerar um `JSONResponse`
por defeito e quando retornar um tipo de codificador personalizado, existem algumas limitações para isso.

Por exemplo, e se quiser retornar com um `status_code` diferente? Ou até mesmo adicionar-lhe uma [tarefa](./tasks.md)?

O codificador personalizado **não lida** com isso para si, mas o `make_response` lida!

Vejamos como ficaria agora utilizando o `make_response`.

```python
{!> ../../../docs_src/encoders/make_response.py !}
```
