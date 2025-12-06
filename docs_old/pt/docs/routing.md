# Routing

O Lilya possui um sistema de roteamento simples, mas altamente eficaz, capaz de lidar desde rotas simples até as mais complexas.

Usando uma aplicação empresarial como exemplo, o sistema de roteamento certamente não será algo simples com 20 ou 40 rotas diretas,
talvez tenha 200 ou 300 rotas onde essas são divididas por responsabilidades, componentes e pacotes e também importadas dentro de sistemas de design complexos.
O Lilya lida com esses casos sem nenhum tipo de problema.

## Router

O Router é o objecto principal que liga todo o Lilya ao [Path](#path), [WebSocketPath](#websocketpath) e [Include](#include).

## Classe Router

A classe do router é composta por muitos atributos que são preenchidos por defeito dentro da aplicação, mas o Lilya também permite adicionar [routers personalizados](#custom-router) adicionais, bem como adicionar uma aplicação [ChildLilya](#child-lilya-application).

```python
{!> ../../../docs_src/routing/router/router_class.py!}
```

A classe principal `Router` é instanciada dentro da aplicação `Lilya` com as rotas fornecidas e a aplicação é iniciada.

### Parâmetros

Ao criar um *handler* [Path](#path) ou [WebSocketPath](#websocketpath), tem duas maneiras de obter os parâmetros do caminho.

* Lilya descobre e injeta automaticamente.
* Obtém-nos directamente do objecto [request](./requests.md).

#### Descobrindo automaticamente os parâmetros

Esta é provavelmente a maneira mais fácil e simples.

```python
{!> ../../../docs_src/routing/handlers/patch.py !}
```

O `customer_id` declarado no `path` também foi declarado no *handler*, permitindo que o Lilya injete os **valores encontrados por ordem dos parâmetros do caminho**.

#### A partir dos parâmetros do caminho do `request`.

```python
{!> ../../../docs_src/routing/handlers/request.py !}
```

O `customer_id` declarado no `path` foi obtido acedendo ao objecto `request`.

## Router Personalizado

Vamos supor que existam submódulos específicos de **clientes** dentro de um ficheiro dedicado `customers`.
Existem duas maneiras de separar as rotas dentro da aplicação, utilizando [Include](#include), um [ChildLilya](#childlilya-application) ou criando outro router. Vamos focar neste último.

```python title="/application/apps/routers/customers.py"
{!> ../../../docs_src/routing/router/customers.py!}
```

Acima, cria o `/application/apps/routers/customers.py` com todas as informações necessárias. Não precisa estar num único ficheiro, pode ter um pacote completamente separado apenas para gerir o cliente.

Agora precisa adicionar o novo router personalizado à aplicação principal.

```python title="/application/app.py"
{!> ../../../docs_src/routing/router/app.py!}
```

Isto é simples e o router é adicionado à aplicação principal do **Lilya**.

## Aplicação ChildLilya

O que é isto? Chamamos de `ChildLilya`, mas na verdade é apenas o Lilya, mas com um nome diferente, principalmente para fins de visualização e organização.

### Como funciona

Vamos usar o mesmo exemplo utilizado nos [routers personalizados](#custom-router) com as rotas e regras específicas dos clientes.

```python title="/application/apps/routers/customers.py"
{!> ../../../docs_src/routing/router/childlilya/customers.py!}
```

Como o `ChildLilya` é uma representação de uma classe [Lilya](./applications.md), podemos passar os parâmetros limitados do [router personalizado](#custom-router) e todos os parâmetros disponíveis no [Lilya](./applications.md).

Pode adicionar quantos `ChildLilya` desejar, não há limites.

**Agora na aplicação principal**:

```python title="/application/app.py"
{!> ../../../docs_src/routing/router/childlilya/app.py!}
```

**Adicionando aplicações *nested***

```python title="/application/app.py"
{!> ../../../docs_src/routing/router/childlilya/nested.py!}
```

O exemplo acima mostra que pode até adicionar a mesma aplicação dentro de includes *nested* e para cada include, pode adicionar [permissões](./permissions.md) e [middlewares](./middleware.md) específicos, que estão disponíveis em cada instância do `Include`. As opções são infinitas.

!!! Note
    Em termos de organização, o `ChildLilya` tem uma abordagem limpa para isolamento de responsabilidades e permite tratar cada módulo individualmente e simplesmente adicioná-lo à aplicação principal sobe a forma de [Include](#include).

!!! Tip
    Trate o `ChildLilya` como uma instância independente do `Lilya`.

!!! Check
    Ao adicionar uma aplicação `ChildLilya` ou `Lilya`, não se esqueça de adicionar o caminho único para o [Include](#include) base, dessa forma pode garantir que as rotas sejam corretamente encontradas.

## Utilitários

O objecto `Router` possui algumas funcionalidades disponíveis que podem ser úteis.

### add_route()

```python
{!> ../../../docs_src/routing/router/add_route.py!}
```

#### Parâmetros

* **path** - O caminho para o ChildLilya.
* **name** - Nome da rota.
* **handler** - O *handler*.
* **methods** - Os verbos HTTP disponíveis para o caminho.
* **include_in_schema** - Se a rota deve ser adicionada ao OpenAPI Schema (se tiver algum).
* **permissions** - Uma lista de [permissões](./permissions.md) para atender aos pedidos de entrada da aplicação (HTTP e Websockets).
* **middleware** - Uma lista de [middlewares](./middleware.md) para executar em cada pedido.
* **exception handlers** - Um dicionário de tipos de [excepção](./exceptions.md) (ou excepções personalizadas) e os *handlers* no nível superior da aplicação. Os *exception handlers* devem ter a forma `handler(request, exc) -> response` e podem ser funções padrão ou funções assíncronas.

### add_websocket_route()

```python
{!> ../../../docs_src/routing/router/add_websocket_route.py!}
```

#### Parâmetros

* **path** - O caminho para o ChildLilya.
* **name** - Nome da rota.
* **handler** - O *handler*.
* **permissions** - Uma lista de [permissões](./permissions.md) para atender aos pedidos de entrada da aplicação (HTTP e Websockets).
* **middleware** - Uma lista de [middlewares](./middleware.md) para executar em cada pedido.
* **exception handlers** - Um dicionário de tipos de [exceção](./exceptions.md) (ou exceções personalizadas) e os *handlers* no nível superior da aplicação. Os *exception handlers* devem ter a forma `handler(request, exc) -> response` e podem ser funções padrão ou funções assíncronas.

### add_child_lilya()

```python
{!> ../../../docs_src/routing/router/add_child_lilya.py!}
```

#### Parâmetros

* **path** - O caminho para o ChildLilya.
* **child** - A instância [ChildLilya](#child-lilya-application).
* **name** - Nome da rota.
* **handler** - O *handler*.
* **permissions** - Uma lista de [permissões](./permissions.md) para atender aos pedidos de entrada da aplicação (HTTP e Websockets).
* **middleware** - Uma lista de [middlewares](./middleware.md) para executar em cada pedido.
* **exception handlers** - Um dicionário de tipos de [exceção](./exceptions.md) (ou exceções personalizadas) e os *handlers* no nível superior da aplicação. Os *exception handlers* devem ter a forma `handler(request, exc) -> response` e podem ser funções padrão ou funções assíncronas.
* **include_in_schema** - Booleano se este ChildLilya deve ser incluído no esquema.
* **deprecated** - Booleano se este ChildLilya deve ser marcado como obsoleto.

## Path

O objecto que liga e constrói as URLs ou caminhos da aplicação. Ele mapeia o *handler* com o sistema de roteamento da aplicação.

#### Parâmetros

* **path** - O caminho para o ChildLilya.
* **name** - Nome da rota.
* **handler** - O *handler*.
* **methods** - Os verbos HTTP disponíveis para o caminho.
* **include_in_schema** - Se a rota deve ser adicionada ao OpenAPI Schema.
* **permissions** - Uma lista de [permissões](./permissions.md) para atender aos pedidos de entrada da aplicação (HTTP e Websockets).
* **middleware** - Uma lista de [middlewares](./middleware.md) para executar em cada pedido.
* **exception handlers** - Um dicionário de tipos de [exceção](./exceptions.md) (ou exceções personalizadas) e os *handlers* no nível superior da aplicação. Os *exception handlers* devem ter a forma `handler(request, exc) -> response` e podem ser funções padrão ou funções assíncronas.
* **deprecated** - Booleano se este ChildLilya deve ser marcado como obsoleto.

=== "Em poucas palavras"

    ```python
    {!> ../../../docs_src/routing/routes/gateway_nutshell.py!}
    ```

## WebSocketPath

O mesmo princípio do [Path](#path) com uma particularidade. Os websockets são `async`.

#### Parâmetros

* **path** - O caminho para o ChildLilya.
* **name** - Nome da rota.
* **handler** - O *handler*.
* **include_in_schema** - Se a rota deve ser adicionada ao OpenAPI Schema.
* **permissions** - Uma lista de [permissões](./permissions.md) para atender aos pedidos de entrada da aplicação (HTTP e Websockets).
* **middleware** - Uma lista de [middlewares](./middleware.md) para executar em cada pedido.
* **exception handlers** - Um dicionário de tipos de [exceção](./exceptions.md) (ou exceções personalizadas) e os *handlers* no nível superior da aplicação. Os *exception handlers* devem ter a forma `handler(request, exc) -> response` e podem ser funções padrão ou funções assíncronas.
* **deprecated** - Booleano se este ChildLilya deve ser marcado como obsoleto.

=== "Em poucas palavras"

    ```python
    {!> ../../../docs_src/routing/routes/websocket_nutshell.py!}
    ```

## Include

Os Includes são exclusivos do Lilya, poderosos e com mais controlo, permitindo:

1. Escalabilidade sem problemas.
2. Design de roteamento limpo.
3. *Separation of Concerns*.
4. Separação de rotas.
5. Redução do nível de importações necessárias através de ficheiros.
6. Menos erros humanos.

!!! Warning
    Os Includes **NÃO** aceitam parâmetros de caminho. Por exemplo: `Include('/include/{id:int}, routes=[...])`.

### Include e aplicação

Este é um objecto muito especial que permite a importação de qualquer rota de qualquer lugar da aplicação.
O `Include` aceita a importação via `namespace` ou via lista `routes`, mas não ambos.

Ao usar um `namespace`, o `Include` procurará a lista padrão `route_patterns` no namespace (objecto) importado, a menos que um `pattern` diferente seja especificado.

O padrão só funciona se as importações forem feitas via `namespace` e não via objecto `routes`.

#### Parâmetros

* **path** - O caminho para o ChildLilya.
* **app** - Uma aplicação pode ser qualquer coisa tratada como uma aplicação ASGI. O `app` pode ser uma aplicação relacionada com ASGI ou uma string `<dotted>.<module>` com a localização da aplicação.
* **routes** - Uma lista global de rotas Lilya. Essas rotas podem variar e podem ser `Path`, `WebSocketPath` ou até mesmo outro `Include`.
* **namespace** - Uma string com um namespace qualificado de onde as URLs devem ser carregadas.
* **pattern** - Uma string com informações de `pattern` de onde as URLs devem ser lidas.
* **name** - Nome do Include.
* **permissions** - Uma lista de [permissões](./permissions.md) para atender aos pedidos de entrada da aplicação (HTTP e Websockets).
* **middleware** - Uma lista de [middlewares](./middleware.md) para executar em cada pedido.
* **exception handlers** - Um dicionário de tipos de [exceção](./exceptions.md) (ou exceções personalizadas) e os *handlers* no nível superior da aplicação. Os *exception handlers* devem ter a forma `handler(request, exc) -> response` e podem ser funções padrão ou funções assíncronas.
* **include_in_schema** - Se a rota deve ser adicionada ao OpenAPI Schema.
* **deprecated** - Booleano se este `Include` deve ser marcado como obsoleto.

=== "Importando utilizando namespace"

    ```python title='myapp/urls.py'
    {!> ../../../docs_src/routing/routes/include/with_namespace.py!}
    ```

=== "Importando utilizando lista de rotas"

    ```python title='src/myapp/urls.py'
    {!> ../../../docs_src/routing/routes/include/routes_list.py!}
    ```

=== "Importar a aplicação via string"

    Esta é uma alternativa para carregar a aplicação via importação `string` em vez de passar o objecto diretamente.

    ```python title='src/myapp/urls.py'
    {!> ../../../docs_src/routing/routes/include/app_str.py!}
    ```

#### Usando um padrão diferente

```python title="src/myapp/accounts/controllers.py"
{!> ../../../docs_src/routing/routes/include/views.py!}
```

```python title="src/myapp/accounts/urls.py"
{!> ../../../docs_src/routing/routes/include/different_pattern.py!}
```

=== "Importando utilizando namespace"

    ```python title='src/myapp/urls.py'
    {!> ../../../docs_src/routing/routes/include/namespace.py!}
    ```

#### Include e instância da aplicação

O `Include` pode ser muito útil, principalmente quando o objetivo é evitar muitas importações e uma lista massiva de objectos a serem passados para um único objecto. Isso pode ser especialmente útil para criar um objecto Lilya limpo.

**Exemplo**:

```python title='src/urls.py'
{!> ../../../docs_src/routing/routes/include/app/urls.py!}
```

```python title='src/app.py'
{!> ../../../docs_src/routing/routes/include/app/app.py!}
```

## Rotas *nested*

À medida que a complexidade aumenta e o nível de rotas também aumenta, o `Include` permite rotas *nested* de forma limpa.

=== "*Nested* simples"

    ```python hl_lines="9"
    {!> ../../../docs_src/routing/routes/include/nested/simple.py!}
    ```

=== "Rotas *nested* complexas"

    ```python hl_lines="10-41"
    {!> ../../../docs_src/routing/routes/include/nested/complex.py!}
    ```

`Include` suporta quantas rotas *nested* com caminhos e Includes diferentes desejar ter. Assim que a aplicação é iniciada, as rotas são montadas e imediatamente disponíveis.

Rotas *nested* também permitem todas as funcionalidades em cada nível, desde middlewares até permissões.

### Rotas da aplicação

!!! Warning
    Tenha muito cuidado ao utilizar o `Include` diretamente no Lilya(routes[]), importar sem um `path` pode resultar nalgumas rotas não serem mapeadas corretamente.

**Aplicável apenas às rotas da aplicação**:

Se decidir fazer isso:

```python
{!> ../../../docs_src/routing/routes/careful/example1.py!}
```

## Host

Se deseja utilizar rotas distintas para o mesmo caminho, dependendo do cabeçalho Host, o Lilya fornece uma solução.

É importante observar que o porto é ignorado do cabeçalho Host durante a correspondência. Por exemplo,
`Host(host='example.com:8081', ...)` será processado independentemente de o cabeçalho Host conter um porto diferente de 8081 (por exemplo, `example.com:8083`, `example.org`). Portanto, se o porto for essencial para fins de `url_path_for`, pode especificá-la explicitamente.

Existem várias abordagens para estabelecer rotas baseadas em host para o sua aplicação.

```python
{!> ../../../docs_src/routing/routes/host.py !}
```

As pesquisas de URL podem abranger parâmetros de host, assim como os parâmetros de caminho são incluídos.

```python
{!> ../../../docs_src/routing/routes/host_encompass.py !}
```
## Prioridade das Rotas

As rotas da aplicação são simplesmente prioritizadas. Os caminhos de entrada são comparados com cada [Path](#path), [WebSocketPath](#websocketpath) e [Include](#include) ordenados.

Nos casos em que mais de um Path pode corresponder a um caminho de entrada, deve garantir que as rotas mais específicas sejam listadas antes dos casos gerais.

Exemplo:

```python
{!> ../../../docs_src/routing/routes/routes_priority.py!}
```

## Parâmetros de Caminho

Os caminhos podem usar um estilo de *template* para os componentes do caminho. Os parâmetros de caminho são aplicados apenas a [Path](#path) e [WebSocketPath](#websocketpath) e **não são aplicados** ao [Include](#include).

**Lembre-se de que existem [duas maneiras de lidar com os parâmetros de caminho](#descobrindo-automaticamente-os-parâmetros)**.

```python
async def customer(customer_id: Union[int, str]) -> None:
    ...


async def floating_point(number: float) -> None:
    ...

Path("/customers/{customer_id}/example", handler=customer)
Path("/floating/{number:float}", handler=customer)
```

Por defeito, isto capturará caracteres até o final do caminho do próximo `/` e se ficará `/customers/{customer_id}/example`.

**Transformadores** podem ser usados para modificar o que está a ser capturado e o tipo do que está a ser capturado. O Lilya fornece alguns transformadores de caminho por defeito.

* `str` retorna uma string e é o padrão.
* `int` retorna um inteiro Python.
* `float` retorna um float Python.
* `uuid` retorna uma instância `uuid.UUID` Python.
* `path` retorna o restante caminho, incluindo quaisquer caracteres `/` adicionais.
* `datetime` retorna a data e hora.

Conforme o padrão, os transformadores são usados prefixando-os com dois pontos:

```python
Path('/customers/{customer_id:int}', handler=customer)
Path('/floating-point/{number:float}', handler=floating_point)
Path('/uploaded/{rest_of_path:path}', handler=uploaded)
```

### Transformadores Personalizados

Se houver a necessidade de um transformador diferente que não esteja definido ou disponível, também pode criar o seu.

```python
{!> ../../../docs_src/routing/routes/transformer_example.py!}
```

Com o transformador personalizado criado, agora pode usá-lo.

```python
Path('/network/{address:ipaddress}', handler=network)
```

## Middlewares, Exception Handlers e Permissões

### Exemplos

Os exemplos a seguir são aplicados à [Path](#path), [WebSocketPath](#websocketpath) e [Include](#include).

Usaremos o Path, pois pode ser substituído por qualquer um dos acima, visto que é comum entre eles.

#### Middlewares

Conforme especificado anteriormente, os [middlewares](./middleware.md) de um Path são lidos de cima para baixo, do pai até o próprio *handler*, e o mesmo é aplicado aos [*exception handlers*](./exceptions.md) e [permissões](./permissions.md).

```python
{!> ../../../docs_src/routing/routes/middleware.py!}
```

O exemplo acima ilustra os vários níveis em que um middleware pode ser implementado e, porque segue uma ordem de pai, a ordem é:

1. Middlewares internos padrão da aplicação.
2. `RequestLoggingMiddlewareProtocol`.
3. `ExampleMiddleware`.

**Mais do que um middleware pode ser adicionado a cada lista.**

#### Exception Handlers

```python
{!> ../../../docs_src/routing/routes/exception_handlers.py!}
```

O exemplo acima ilustra os vários níveis em que os *exception handlers* podem ser implementados e segue uma ordem de pai, onde a ordem é:

1. *Exception handlers* internos padrão da aplicação.
3. `InternalServerError: http_internal_server_error_handler`.
4. `NotAuthorized: http_not_authorized_handler`.

**Mais de um *handler* pode ser adicionado a cada mapeamento.**

#### Permissões

Permissões são obrigatórias em **todas** as aplicações. Saiba mais sobre [permissões](./permissions.md) e como usá-las.

```python
{!> ../../../docs_src/permissions/any_other_level.py!}
```

**Mais de uma permissão pode ser adicionada a cada lista.**

## Pesquisa Reversa de Caminho

Frequentemente, há a necessidade de gerar o URL para uma rota específica, especialmente em cenários em que uma resposta de reencaminhamento é necessária.

```python
{!> ../../../docs_src/routing/routes/lookup.py!}
```

As pesquisas também permitem parâmetros de caminho.

```python
{!> ../../../docs_src/routing/routes/lookup_path.py!}
```

Se um `Include` incluir um nome, as submontagens subsequentes devem usar o formato `{prefix}:{name}` para pesquisas de caminho reverso.

### Usando o `reverse`

Esta é uma alternativa para a pesquisa reversa de caminho. Pode ser particularmente útil se você quiser reverter um caminho em testes ou isoladamente.

#### Parâmetros

* **name** - O nome atribuído ao caminho.
* **app** - Uma aplicação ASGI que contém as rotas. Útil para reverter caminhos em aplicações específicas e/ou testes. *(Opcional)*.
* **path_params** - Um objecto semelhante a um dicionário contendo os parâmetros que devem ser passados num determinado caminho. *(Opcional)*.

Ao usar o `reverse`, se nenhum parâmetro `app` for especificado, será automaticamente definido como a aplicação ou roteador de aplicação, que em circunstâncias normais, para além de `testing`, é o comportamento esperado.

```python
{!> ../../../docs_src/routing/routes/reverse.py!}
```

O `reverse` também permite parâmetros de caminho.

```python
{!> ../../../docs_src/routing/routes/reverse_path.py!}
```
