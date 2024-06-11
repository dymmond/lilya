# WebSocket

O Lilya fornece uma classe `WebSocket` que desempenha uma função comparável a um pedido HTTP, mas facilita a troca de dados por meio de um WebSocket, permitindo operações de envio e recepção.

### WebSocket

```python
{!> ../../../docs_src/websockets/websocket.py !}
```

WebSockets apresentam uma interface de mapeamento, então pode usá-los da mesma forma que um `scope`.

Por exemplo: `websocket['path']` retornará o caminho ASGI.

#### URL

O URL do WebSocket é acedida via `websocket.url`.

O acesso ao URL do WebSocket é feito utilizando `websocket.url`. Esta propriedade, uma subclasse de `str`, não apenas representa o próprio URL, mas também expõe todos os componentes individuais que podem ser extraídos do URL.

```python
from lilya.websockets import WebSocket

websocket = WebSocket(scope, receive, send)

websocket.url.scheme
websocket.url.path
websocket.url.port
```

#### Cabeçalho

Lilya usa o [multidict](https://multidict.aio-libs.org/en/stable/) para os seus cabeçalhos (headers) e adiciona alguns extras em cima.

```python
from lilya.websockets import WebSocket

websocket = WebSocket(scope, receive, send)

websocket.headers['sec-websocket-version']
```

#### Parâmetros de Consulta

Lilya usa o [multidict](https://multidict.aio-libs.org/en/stable/) para seus parâmetros de consulta (query params) e adiciona alguns extras em cima.

```python
from lilya.websockets import WebSocket

websocket = WebSocket(scope, receive, send)

websocket.query_params['search']
```

#### Parâmetros de Caminho

Extraído diretamente do `scope` como um dicionário em Python.

```python
from lilya.websockets import WebSocket

websocket = WebSocket(scope, receive, send)

websocket.path_params['username']
```

### Operações

#### Aceitando conexão

* `await websocket.accept(subprotocol=None, headers=None)`

#### Enviando dados

* `await websocket.send_text(data)`
* `await websocket.send_bytes(data)`
* `await websocket.send_json(data)`

Mensagens JSON são enviadas por defeito utilizando *frames* de dados de texto.
Para enviar JSON sobre *frames* de dados binários, utilize `websocket.send_json(data, mode="binary")`.

#### Recebendo dados

* `await websocket.receive_text()`
* `await websocket.receive_bytes()`
* `await websocket.receive_json()`

!!! warning
    É importante observar que a operação pode gerar `lilya.websockets.WebSocketDisconnect()`.

Mensagens JSON são automaticamente recebidas sobre *frames* de dados de texto por defeito.
Para receber JSON sobre *frames* de dados binários, utilize `websocket.receive_json(data, mode="binary")`.

#### Iterando dados

* `websocket.iter_text()`
* `websocket.iter_bytes()`
* `websocket.iter_json()`

Assim como `receive_text`, `receive_bytes` e `receive_json`, esta função retorna um iterador assíncrono.

```python
{!> ../../../docs_src/websockets/example.py !}
```

Quando ocorre o `lilya.websockets.WebSocketDisconnect`, o iterador será encerrado.

#### Fechando a conecção

* `await websocket.close(code=1000, reason=None)`

#### Enviando e recebendo mensagens

Nos casos em que é necessário enviar ou receber mensagens ASGI brutas, é aconselhável utilizar
`websocket.send()` e `websocket.receive()` em vez de empregar diretamente as chamadas brutas `send` e `receive`.
Esta abordagem garante a manutenção adequada do estado interno do WebSocket.

* `await websocket.send(message)`
* `await websocket.receive()`

#### Enviar Resposta de Negação

Caso `websocket.close()` seja invocado antes de `websocket.accept()`, o servidor automaticamente
enviará um erro HTTP 403 para o cliente.

Para respostas de erro personalizadas (responses), o método `websocket.send_denial_response()` pode ser utilizado.
Este método facilita a transmissão da resposta especificada antes de fechar a conecção.

* `await websocket.send_denial_response(response)`

!!! warning
    Essa funcionalidade depende do servidor ASGI suportar a extensão de *Denial Response* do WebSocket.
    Na ausência de suporte, tentar utilizá-la resultará em `RuntimeError`.
