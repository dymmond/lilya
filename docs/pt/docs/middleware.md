# Middleware

O Lilya inclui vários middlewares exclusivos da aplicação, mas também permite algumas maneiras de os criar utilizando `protocolos`.

## Middleware Lilya

O middleware Lilya é a maneira clássica já disponível de declarar o middleware dentro de uma aplicação **Lilya**.

```python
{!> ../../../docs_src/middleware/lilya_middleware.py !}
```

## Protocolos Lilya

Os protocolos Lilya não são muito diferentes do [middleware Lilya](#middleware-lilya). Na verdade, o nome em si só existe por causa do uso dos [protocolos Python](https://peps.python.org/pep-0544/), que forçam uma certa estrutura.

Ao criar um middleware, pode herdar o **MiddlewareProtocol** fornecido pelo Lilya.

```python
{!> ../../../docs_src/middleware/protocols.py !}
```

### MiddlewareProtocol

Para aqueles que estão habituados a linguagens de programação com forte enfase no *static typing*, como Java ou C#, um protocolo é o equivalente em Python a uma interface.

O `MiddlewareProtocol` é simplesmente uma interface para construir middlewares para o **Lilya**, forçando a implementação dos métodos `__init__` e `async def __call__`.

O uso desse protocolo também está alinhado com a criação de um [Middleware ASGI Puro](#middleware-asgi-puro).

### Exemplo rápido

```python
{!> ../../../docs_src/middleware/sample.py !}
```

## Middleware e a aplicação

A criação deste tipo de middleware garantirá que os protocolos sejam seguidos, reduzindo assim erros de desenvolvimento ao remover erros comuns.

Para adicionar middlewares à aplicação é muito simples.

=== "Nível da aplicação"

    ```python
    {!> ../../../docs_src/middleware/adding_middleware.py !}
    ```

=== "Qualquer outro nível"

    ```python
    {!> ../../../docs_src/middleware/any_other_level.py !}
    ```

### Nota rápida

!!! Info
    O middleware não se limita ao `Lilya`, `ChildLilya`, `Include` e `Path`. Apenas foi escolhido o `Path` porque é mais simples de ler e perceber.

## Middleware ASGI Puro

O Lilya segue a especificação do [ASGI](https://asgi.readthedocs.io/en/latest/). Essa capacidade permite a implementação de middlewares ASGI utilizando a interface ASGI diretamente. Isso envolve a criação de uma cadeia de aplicações ASGI que chamam o seguinte.

A abordagem espelha a implementação das classes middleware fornecidas pelo Lilya.

**Exemplo da abordagem mais comum**

```python
from lilya.types import ASGIApp, Scope, Receive, Send


class MyMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        await self.app(scope, receive, send)
```

Ao implementar um middleware ASGI Puro, é como implementar uma aplicação ASGI, o primeiro parâmetro **deve ser sempre uma aplicação**
e o método `__call__` **deve retornar sempre a aplicação**.

## BaseAuthMiddleware

Este é um middleware muito especial e ajuda qualquer middleware relacionado com autenticação que pode ser usado numa aplicação **Lilya**,
mas, como tudo, também pode criar o seu próprio e ignorar isto.

`BaseAuthMiddleware` é também um protocolo que simplesmente força a implementação do método `authenticate` e atribui o objecto de resultado a um `AuthResult`
para torná-lo disponível em cada pedido.

### Exemplo de uma classe de middleware JWT

```python title='/src/middleware/jwt.py'
{!> ../../../docs_src/middleware/auth_middleware_example.py !}
```

1. Importe o `BaseAuthMiddleware` de `lilya.middleware.authentication`.
2. Implemente o método `authenticate` e atribua o resultado `user` ao `tuple[AuthCredentials, UserInterface]` (AuthResult).

#### Importe o middleware numa aplicação Lilya

=== "A partir da instância da aplicação"

    ```python
    from lilya import Lilya
    from lilya.middleware import DefineMiddleware
    from .middleware.jwt import JWTAuthMiddleware


    app = Lilya(routes=[...], middleware=[DefineMiddleware(JWTAuthMiddleware)])
    ```

=== "A partir das definições"

    ```python
    from typing import List

    from lilya.conf.global_settings import Settings
    from lilya.middleware import DefineMiddleware
    from .middleware.jwt import JWTAuthMiddleware


    class AppSettings(Settings):

        @property
        def middleware(self) -> List[DefineMiddleware]:
            return [
                DefineMiddleware(JWTAuthMiddleware)
            ]

    # carregue as definições via LILYA_SETTINGS_MODULE=src.configs.live.AppSettings
    app = Lilya(routes=[...])
    ```

!!! Tip
    Para saber mais sobre como carregar as definições e as propriedades disponíveis, consulte a documentação das [definições](./settings.md).

## Middleware e as definições

Uma das vantagens do Lilya é aproveitar as definições para tornar o código organizado, limpo e fácil de manter.
Conforme mencionado no documento de [definições](./settings.md), o middleware é uma das propriedades disponíveis para iniciar uma aplicação Lilya.

```python title='src/configs/live.py'
{!> ../../../docs_src/middleware/settings.py !}
```

**Inicie a aplicação com as novas definições**

```shell
LILYA_SETTINGS_MODULE=configs.live.AppSettings palfrey src:app

INFO:     Listening on ('127.0.0.1', 8000) (Press CTRL+C to quit)
INFO:     Started reloader process [28720]
INFO:     Started server process [28722]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

!!! Warning
    Se o `LILYA_SETTINGS_MODULE` não for especificado como o módulo a ser carregado, o **Lilya** carregará as definições padrão,
    mas o seu middleware não será inicializado.

### Importante

Se precisar especificar parâmetros no seu middleware, será necessário encapsulá-lo num objecto `lilya.middleware.DefineMiddleware`.
Veja o exemplo do `GZipMiddleware` [aqui](#middleware-e-as-definições).

## Middlewares disponíveis

* `CSRFMiddleware` - Lida com CSRF.
* `CORSMiddleware` - Lida com CORS.
* `TrustedHostMiddleware` - Lida com CORS se um `allowed_hosts` específico estiver definido.
* `GZipMiddleware` - Middleware de compressão `gzip`.
* `HTTPSRedirectMiddleware` - Middleware que lida com redirecionamentos HTTPS para a sua aplicação. Muito útil para uso em ambientes de produção ou semelhantes a produção.
* `SessionMiddleware` - Middleware que lida com sessões.
* `WSGIMiddleware` - Permite ligar aplicações WSGI e executá-los dentro do Lilya. Um [ótimo exemplo](./wsgi.md) de como usá-lo está disponível.
* `XFrameOptionsMiddleware` - Middleware que lida especificamente contra clickjacking.
* `SecurityMiddleware` - Fornece várias melhorias de segurança ao ciclo de pedido/resposta e adiciona cabeçalhos de segurança à resposta.

### CSRFMiddleware

Os parâmetros padrão usados na implementação do CSRFMiddleware são restritivos por defeito e o Lilya permite algumas maneiras de usar esse middleware, dependendo das preferências.

```python
{!> ../../../docs_src/middleware/available/csrf.py !}
```

### CORSMiddleware

Os parâmetros padrão usados na implementação do CORSMiddleware são restritivos por defeito e o Lilya permite algumas maneiras de usar esse middleware, dependendo das preferências.

```python
{!> ../../../docs_src/middleware/available/cors.py !}
```

### SessionMiddleware

Adiciona sessões HTTP baseadas em cookies assinados. As informações da sessão são legíveis, mas não modificáveis.

```python
{!> ../../../docs_src/middleware/available/sessions.py !}
```

### HTTPSRedirectMiddleware

Garante que todos os pedidos recebidas devem ser https ou wss. Qualquer pedido http ou ws será redirecionado para o formato seguro correspondente.

```python
{!> ../../../docs_src/middleware/available/https.py !}
```

### TrustedHostMiddleware

Exige que todos os pedidos tenham um cabeçalho `Host` corretamente definido para proteção contra ataques *host header*.

```python
{!> ../../../docs_src/middleware/available/trusted_hosts.py !}
```

### GZipMiddleware

Lida com respostas GZip para qualquer pedido que inclua "gzip" no cabeçalho Accept-Encoding.

```python
{!> ../../../docs_src/middleware/available/gzip.py !}
```

### WSGIMiddleware

Uma classe de middleware responsável por converter uma aplicação WSGI numa aplicação ASGI. Existem mais exemplos na secção [Frameworks WSGI](./wsgi.md).

```python
{!> ../../../docs_src/middleware/available/wsgi.py !}
```

O `WSGIMiddleware` também permite passar a `app` como uma string `<dotted>.<path>`, o que pode facilitar a organização do código.

Vamos supor que o exemplo anterior da aplicação `flask` estivesse dentro da `myapp/asgi_or_wsgi/apps`. Ficaria desta forma:

```python
{!> ../../../docs_src/middleware/available/wsgi_str.py !}
```

Para chamá-lo dentro do middleware é tão simples quanto isto:

```python
{!> ../../../docs_src/middleware/available/wsgi_import.py !}
```

### XFrameOptionsMiddleware

O middleware de clickjacking fornece proteção fácil de usar contra ataques de clickjacking.
Este tipo de ataque ocorre quando um site malicioso engana um utilizador para clicar num elemento oculto de outro site que eles carregaram num iframe oculto.

Este middleware lê o valor `x_frame_options` das [configurações](./settings.md) e tem como valor padrão `DENY`.

Ele também adiciona o cabeçalho `X-Frame-Options` às respostas.

```python
{!> ../../../docs_src/middleware/available/clickjacking.py !}
```

### SecurityMiddleware

Fornece várias melhorias de segurança no ciclo de pedido/resposta e adiciona cabeçalhos de segurança à resposta.

```python
{!> ../../../docs_src/middleware/available/security.py !}
```

### Outros middlewares

Pode desenhar os seus próprios middlewares conforme explicado acima, mas também reutilizar middlewares diretamente para qualquer outra aplicação ASGI, se assim o desejar.
Se os middlewares seguirem a abordagem do [ASGI puro](#middleware-asgi-puro), eles serão 100% compatíveis.

#### <a href="https://github.com/abersheeran/asgi-ratelimit">RateLimitMiddleware</a>

Um Middleware ASGI para limitar a taxa de pedidos e altamente personalizável.

#### <a href="https://github.com/snok/asgi-correlation-id">CorrelationIdMiddleware</a>

Uma classe de middleware para ler/gerar IDs de pedido e anexá-los aos logs da aplicação.

!!! Tip
    Para aplicações Lilya, substitua FastAPI por Lilya nos exemplos fornecidos ou implemente da maneira mostrada neste documento.

#### <a href="https://github.com/steinnes/timing-asgi">TimingMiddleware</a>

Middleware ASGI para registrar e emitir métricas de tempo (para algo como statsd).

## Pontos importantes

1. O Lilya oferece suporte ao [middleware Lilya](#middleware-lilya) ([MiddlewareProtocol](#protocolos-lilya)).
2. `MiddlewareProtocol` é simplesmente uma interface que exige a implementação do `__init__` e `async __call__`.
3. `app` é um parâmetro obrigatório para qualquer classe que herda do `MiddlewareProtocol`.
4. É encorajado o uso de [Middleware ASGI Puro](#middleware-asgi-puro) e o `MiddlewareProtocol` exige isso.
1. As classes middleware podem ser adicionadas em qualquer [camada da aplicação](#nota-rápida).
2. Todos os middlewares de autenticação devem herdar do BaseAuthMiddleware.
3. Pode carregar o **middleware da aplicação** de diferentes maneiras.
