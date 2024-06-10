# Controladores

Lilya adopta tanto a metodologia de programação funcional quanto a orientada a objetos (OOP). Dentro da framework Lilya,
o paradigma OOP é chamado de *controller*, uma nomenclatura inspirada noutras tecnologias notáveis.

O `Controller` actua como o orquestrador para lidar com pedidos HTTP padrão e gerir sessões WebSocket.

Internamente, o `Controller` e o `WebSocketController` implementam os mesmos *wrappers* de resposta que o
[Path](./routing.md#path) e [WebSocketPath](./routing.md#websocketpath), garantindo que permanece
como uma única fonte de verdade e isso também significa que a [descoberta automática](./routing.md#auto-discovering-the-parameters) dos
parâmetros também funciona.

## A classe `Controller`

Este objeto também serve como aplicação ASGI, o que significa que abraça a implementação interna
do `__call__` e despacha os pedidos.

Ele também é responsável por implementar apenas o despacho HTTP dos pedidos.

```python
{!> ../../../docs_src/controllers/controller.py!}
```

Quando se utiliza uma instância da aplicação Lilya para gestão de roteamento, tem a opção de despachar para uma classe `Controller`.

!!! warning
    É crucial o despacho directo para a class e não para uma instância.

Aqui está um exemplo para esclarecimento:

```python
{!> ../../../docs_src/controllers/dispatch.py !}
```

Neste caso, a `ASGIApp` classe é despachada, não a instância da classe.

As classes `Controller`, ao encontrarem métodos de pedido que não correspondem a um manipulador correspondente,
responderão automaticamente com respostas `405 Method not allowed`.

## A classe `WebSocketController`

A classe `WebSocketController` serve como uma aplicação ASGI, encapsulando a funcionalidade de uma instância `WebSocket`.

O âmbito da conecção ASGI é acessível na instância do *endpoint* através de `.scope` e possui um atributo chamado `encoding`.
Esse atributo, que pode ser opcionalmente definido, é utilizado para validar os dados esperados do WebSocket no método `on_receive`.

Os tipos de codificação disponíveis são:

- `'json'`
- `'bytes'`
- `'text'`
Existem três métodos que podem ser substituídos para lidar com tipos específicos de mensagens ASGI WebSocket:

1. `async def on_connect(websocket, **kwargs)`
2. `async def on_receive(websocket, data)`
3. `async def on_disconnect(websocket, close_code)`

```python
{!> ../../../docs_src/controllers/websocketcontroller.py !}
```

O `WebSocketController` também é compatível com a classe da aplicação Lilya.

```python
{!> ../../../docs_src/controllers/wdispatch.py !}
```
