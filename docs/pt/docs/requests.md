# Requests

Lilya disponibiliza a classe `Request`. Este objeto é uma interface conveniente entre o pedido recebido e o âmbito ASGI.

Isso significa que você não precisa aceder diretamente ao âmbito e extrair todas as informações necessárias para um objeto do tipo `request`.

```python
from lilya.requests import Request
```

## A classe `Request`

Uma instância de `Request` recebe um parâmetro `scope`, um parâmetro `receive` e um parâmetro `send`.

```python
{!> ../../../docs_src/requests/example.py !}
```

Os pedidos, como mencionado anteriormente, apresentam uma interface para o `scope`, o que significa que se você usar
`request['app']` ou `request['headers']` ou `request['path']`, irá obter as mesmas informações
que estavam a ser obtidas no scope.

### Nota

Se não houver necessidade de aceder ao corpo do pedido, pode instanciar um pedido sem fornecer um argumento `receive`.

**Exemplo**

```python
from lilya.requests import Request

request = Request(scope)
```

### Atributos

Existem muitos atributos disponíveis que pode aceder dentro do request.

#### Método

O método do pedido que é utilizado para aceder.

```python
from lilya.requests import Request

request = Request(scope)

request.method
```

#### URL

```python
from lilya.requests import Request

request = Request(scope)

request.url
```

Esta propriedade expõe todos os componentes que podem ser extraídos da URL.

**Exemplo**

```python
from lilya.requests import Request

request = Request(scope)

request.url.port
request.url.path
request.url.scheme
request.url.netloc
request.url.query
```

#### Cabeçalho

Lilya usa o [multidict](https://multidict.aio-libs.org/en/stable/) para os seus cabeçalhos (headers) e adiciona-lhe
alguns recursos extra.

```python
from lilya.requests import Request

request = Request(scope)

request.headers['content-type']
```

#### Parâmetros de Consulta

Lilya usa o [multidict](https://multidict.aio-libs.org/en/stable/) para os seus parâmetros de consulta (query params) e adiciona-lhe
alguns recursos extra.

```python
from lilya.requests import Request

request = Request(scope)

request.query_params['search']
```

#### Parâmetros de URL

Extraído diretamente do `scope` como um dicionário em Python.

```python
from lilya.requests import Request

request = Request(scope)

request.path_params['username']
```

#### Endereço do Cliente

O endereço remoto do cliente é exposto como uma classe de dados `request.client`.

```python
from lilya.requests import Request

request = Request(scope)

request.client.host
request.client.port
```

#### Cookies

Extraído diretamente dos cabeçalhos (headers) e analisado como um dicionário em Python.

```python
from lilya.requests import Request

request = Request(scope)

request.cookies.get('a-cookie')
```

#### Corpo (body)

Aqui é diferente. Para extrair e usar o `body`, um argumento `send` deve ser passado para a
instância do pedido e pode ser extraído de diferentes maneiras.

##### Como bytes

```python
from lilya.requests import Request

pedido = Request(scope, send)

await request.body()
```

##### Como JSON

```python
from lilya.requests import Request

pedido = Request(scope, send)

await request.json()
```

##### Como texto

```python
from lilya.requests import Request

pedido = Request(scope, send)

await request.text()
```

##### Como dados de formulário ou formulário multipart

```python
from lilya.requests import Request

pedido = Request(scope, send)

async with request.form() as form:
    ...
```

##### Como dados

```python
from lilya.requests import Request

pedido = Request(scope, send)

await request.data()
```

##### Como um stream

```python
{!> ../../../docs_src/requests/stream.py !}
```

Ao usar `.stream()`, os fragmentos de bytes são fornecidos sem a necessidade de guardar todo o corpo em memória.
Chamadas subsequentes a `.body()`, `.form()` ou `.json()` resultarão em erro.

Em situações específicas, como resposta de longa duração ou streaming, torna-se crucial
determinar se o cliente foi desconectado.

Isso pode ser verificado utilizando o seguinte:
`desconectado = await request.is_disconnected().`


##### Ficheiros de Request

Normalmente, os ficheiros são transmitidos como dados de formulário multipart (multipart/form-data).

```python
from lilya.requests import Request

request = Request(scope, receive)

request.form(max_files=1000, max_fields=1000)
```

Tem a flexibilidade de definir o número máximo de campos ou ficheiros usando os parâmetros `max_files`
e `max_fields`:

```python
async with request.form(max_files=1000, max_fields=1000):
    ...
```

!!! warning
    Estas limitações servem para fins de segurança. Permitir um número ilimitado de campos ou ficheiros poderia
    representar um risco de ataque de *denial of service*, consumindo recursos excessivos de CPU e memória
    ao analisar inúmeros campos vazios.

Ao utilizar `async with request.form() as form`, obtém um `lilya.datastructures.FormData`,
que é um multidict imutável contendo tanto uploads de ficheiros quanto *input* de texto.

Os itens de upload de ficheiros são representados como instâncias de `lilya.datastructures.DataUpload`.

###### DataUpload

DataUpload possui os seguintes atributos:

* **filename**: Uma `str` com o nome original do ficheiro que foi enviado ou `None` se não estiver disponível (por exemplo, `profile.png`).
* **file**: Um `SpooledTemporaryFile` (um objeto semelhante a um ficheiro). Este é o ficheiro Python real que pode passar diretamente para outras
funções ou bibliotecas que esperam um objeto "semelhante a um ficheiro".
* **headers**: Um objeto `Header`. Geralmente, isso será apenas o cabeçalho `Content-Type`, mas se houver cabeçalhos adicionais
incluídos no campo multipart, serão incluídos aqui. Observe que esses cabeçalhos não têm relação com os cabeçalhos em `Request.headers`.
* **size**: Um `int` com o tamanho do ficheiro enviado em bytes. Esse valor é calculado a partir do conteúdo do pedido, tornando-o uma escolha melhor para encontrar o tamanho do ficheiro enviado do que o cabeçalho `Content-Length`. Nenhum valor se não estiver definido.

A classe `DataUpload` fornece vários métodos assíncronos que invocam as operações de ficheiro correspondentes usando o `SpooledTemporaryFile` interno:

* `async write(dados)`: Grava os dados especificados (em bytes) no ficheiro.
* `async read(tamanho)`: Lê o número especificado de bytes (como um inteiro) do ficheiro.
* `async seek(deslocamento)`: Posiciona o cursor do ficheiro na posição de bytes especificado (como um inteiro).
Por exemplo, usando `await profile.seek(0)` moveria o cursor para o início do ficheiro.
* `async close()`: Fecha o ficheiro.

Como todos estes métodos são assíncronos, a palavra-chave `await` é necessária ao invocá-los.

**Exemplo**

```python
async with request.form() as form:
    filename = form["upload_file"].filename
    contents = await form["upload_file"].read()
```

#### Aplicação

A aplicação Lilya.

```python
from lilya.requests import Request

request = Request(scope)

request.app
```

#### Estado

Se você deseja incluir informações adicionais com o pedido, pode faze-lo usando
o `request.state`.

```python
from lilya.requests import Request

request = Request(scope)

request.state.admin = "example@lilya.dev"
```
