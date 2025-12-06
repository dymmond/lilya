# Permissões

O Lilya incorpora um sistema de permissões inato desenhado para facilitar o princípio de
*separation of concerns*. Interessantemente, esse sistema de permissões é muito parecido com os [middlewares](./middleware.md).

Essencialmente, as permissões no Lilya funcionam como aplicações ASGI puros, semelhantes a middlewares,
mas são especificamente desenvolvidas para gerir acessos à aplicação.

A razão para a introdução de uma nova aplicação ṕarecida à ASGI, mas para permissões,
reside em manter um propósito claro e singular para cada componente. O Lilya garante essa distinção.

As permissões operam na sequência **após o middleware** e **antes de chegar ao handler**,
posicionando-as idealmente para controlar o acesso à aplicação.

## Usando a permissão

A aplicação Lilya fornece uma forma de incluir a permissão ASGI de forma a garantir que permanece encapsulada no *exception handler*.

```python
{!> ../../../docs_src/permissions/sample.py !}
```

Ao definir uma `permissão`, é imprescindível utilizar o `lilya.permissions.DefinePermission` para encapsulá-la.
Além disso, é aconselhável seguir o `PermissionProtocol` do
`lilya.protocols.permissions.PermissionProtocol`, pois fornece uma interface para a definição.

O Lilya inclui uma excepção por defeito especificamente para negar permissões. Tipicamente, ao negar uma permissão,
é mandado um *statuc code* `403` junto com uma mensagem específica. Essa funcionalidade é encapsulada no
`lilya.exceptions.PermissionDenied`.

Além disso, os detalhes da mensagem podem ser personalizados conforme necessário.

### PermissionProtocol

Para aqueles vindos de uma linguagem com *static type* como Java ou C#, um protocolo é equivalente em Python a uma
interface.

O `PermissionProtocol` é simplesmente uma interface para criar permissões para o **Lilya**, mediante a aplicação
da implementação do `__init__` e do `async def __call__`.

O desenho deste protocolo também está alinhado com a [Permissão Pura ASGI](#permissão-pura-asgi).

### Exemplo rápido

```python
{!> ../../../docs_src/permissions/quick_sample.py !}
```

## Permissão e o aplicação

Ao criar esse tipo de permissões, também garante que os protocolos sejam seguidos, reduzindo assim os erros de desenvolvimento
por meio da remoção de erros comuns.

É muito simples adicionar middlewares à aplicação. Podem ser incluídos em qualquer nível da aplicação.
Podem ser inseridos no `Lilya`/`ChildLilya`, `Include`, `Path` e `WebSocketPath`.

=== "Nível do aplicação"

    ```python
    {!> ../../../docs_src/permissions/adding_permission.py !}
    ```

=== "Qualquer outro nível"

    ```python
    {!> ../../../docs_src/permissions/any_other_level.py !}
    ```

## Permissão Pura ASGI

O Lilya segue a especificação [ASGI](https://asgi.readthedocs.io/en/latest/).
Isso permite a implementação de permissões ASGI usando a
interface ASGI diretamente. Isso envolve a criação de uma cadeia de aplicações ASGI que chamam o seguinte.

**Exemplo da abordagem mais comum**

```python
from lilya.types import ASGIApp, Scope, Receive, Send


class MinhaPermissao:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        await self.app(scope, receive, send)
```

Ao implementar uma permissão pura ASGI, é como implementar uma aplicação ASGI, o primeiro parâmetro **deve ser sempre uma aplicação**
e o método `__call__` **deve retornar sempre a aplicação**.

## Permissões e as definições

Uma das vantagens do Lilya é aproveitar as definições para tornar o código-base organizado, limpo e fácil de manter.
Conforme mencionado no documento das [definições](./settings.md), as permissões são uma das propriedades disponíveis
para iniciar uma aplicação Lilya.

```python
{!> ../../../docs_src/permissions/settings.py !}
```
