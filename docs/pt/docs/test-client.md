# Cliente de Teste

O Lilya vem com um cliente de teste para os testes da sua aplicação. Não é obrigatório usá-lo, pois cada aplicação e equipa de desenvolvimento tem sua própria maneira de testar, mas caso precise, está disponível.

## Requisitos

Esta secção requer que a suíte de testes do Lilya esteja instalada. Pode fazer isso executando:

```shell
$ pip install Lilya[test]
```

## O cliente de teste

```python
{!> ../../../docs_src/testclient/example1.py !}
```

Pode usar qualquer uma das APIs padrão do `httpx`, como autenticação, cookies de sessão e envio de ficheiros.

```python
{!> ../../../docs_src/testclient/example2.py !}
```

**TestClient**

```python
{!> ../../../docs_src/testclient/example3.py !}
```

`httpx` é uma ótima biblioteca criada pelo mesmo autor do `Starlette` e do `Django Rest Framework`.

!!! Info
    Por defeito, o TestClient lança qualquer exceção que ocorra na aplicação.
    Ocasionalmente, pode querer testar o conteúdo das respostas de erros 500, em vez de permitir que o cliente lance a exceção do servidor. Nesse caso, deve utilizar `client = TestClient(app, raise_server_exceptions=False)`.

## Eventos de ciclo de vida

!!! Note
    O Lilya suporta todos os eventos de ciclo de vida disponíveis e, portanto, `on_startup`, `on_shutdown` e `lifespan` também são suportados pelo `TestClient` **mas** se
    precisar testá-los, precisará executar o `TestClient` como um gestor de contexto, caso contrário, os eventos não serão acionados quando o `TestClient` for instanciado.

O Lilya também traz uma funcionalidade pronta a usar que pode ser utilizada como um gestor de contexto para testes, o `create_client`.

### Gestor de contexto `create_client`

Esta função está preparada para ser utilizada como um gestor de contexto para testes e está pronta para ser utilizada a qualquer momento.

```python
{!> ../../../docs_src/testclient/example4.py !}
```

Os testes funcionam tanto com funções `sync` quanto `async`.

!!! info
    O exemplo acima também é usado para mostrar que os testes podem ser tão complexos quanto desejar e funcionarão com o gestor de contexto.

## override_settings

Este é um decorator especial do Lilya e serve como auxiliar para os testes quando precisa atualizar/mudar as configurações temporariamente para testar qualquer cenário que exija valores específicos para as configurações terem valores diferentes.

O `override_settings` atua como um decorator normal ou como um gestor de contexto.

As configurações que pode substituir são as declaradas nas [configurações](./settings.md).

```python
from lilya.testclient import override_settings
```

Vejamos um exemplo.

```python
from lilya.apps import Lilya
from lilya.middleware import DefineMiddleware
from lilya.middleware.clickjacking import XFrameOptionsMiddleware
from lilya.responses import PlainText
from lilya.routing import Path
from lilya.testclient.utils import override_settings


@override_settings(x_frame_options="SAMEORIGIN")
def test_xframe_options_same_origin_responses(test_client_factory):
    def homepage():
        return PlainText("Ok", status_code=200)

    app = Lilya(
        routes=[Path("/", handler=homepage)],
        middleware=[DefineMiddleware(XFrameOptionsMiddleware)],
    )

    client = test_client_factory(app)

    response = client.get("/")

    assert response.headers["x-frame-options"] == "SAMEORIGIN"
```

Ou como gestor de contexto.

```python
from lilya.apps import Lilya
from lilya.middleware import DefineMiddleware
from lilya.middleware.clickjacking import XFrameOptionsMiddleware
from lilya.responses import PlainText
from lilya.routing import Path
from lilya.testclient.utils import override_settings


def test_xframe_options_same_origin_responses(test_client_factory):
    def homepage():
        return PlainText("Ok", status_code=200)

    with override_settings(x_frame_options="SAMEORIGIN"):
        app = Lilya(
            routes=[Path("/", handler=homepage)],
            middleware=[DefineMiddleware(XFrameOptionsMiddleware)],
        )

        client = test_client_factory(app)

        response = client.get("/")

        assert response.headers["x-frame-options"] == "SAMEORIGIN"
```
