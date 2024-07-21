# Definições

Em cada aplicação, surge a necessidade de definições específicas do projecto para garantir a sua singularidade.

À medida que um projecto se torna mais complexo e as definições dispersam-se por todo o código-fonte,
geri-las pode se tornar um desafio, levando a uma possível desordem.

!!! warning
    Todas as definições no Lilya usam dataclasses em Python.

## Como utilizar

Existem duas formas de utilizar o objecto de configurações dentro de uma aplicação Lilya.

* Utilizando a variável de ambiente **LILYA_SETTINGS_MODULE**
* Utilizando o atributo de instância **[settings_module](#o-settings_module)**.

Cada um deles tem casos de uso específicos, mas também trabalham juntos em perfeita harmonia.

## Definições e a aplicação

Ao iniciar uma instância do Lilya, se nenhum parâmetro for fornecido, ela carregará automaticamente as configurações
padrão do objecto de configurações do sistema, o `Settings`.

=== "Sem parâmetros"

    ```python
    {!> ../../../docs_src/settings/app/no_parameters.py!}
    ```

=== "Com Parâmetros"

    ```python
    {!> ../../../docs_src/settings/app/with_parameters.py!}
    ```

## Definições personalizadas

Utilizar as configurações padrão do `Settings` geralmente não será suficiente para a maioria das aplicações.

Por essa razão, são necessárias configurações personalizadas.

**Todas as configurações personalizadas devem ser herdadas do `Settings`**.

Vamos supor que temos três ambientes para uma aplicação: `produção`, `teste` e `desenvolvimento`, e um ficheiro de configurações
base que contém configurações comuns aos três ambientes.

=== "Base"

    ```python
    {!> ../../../docs_src/settings/custom/base.py!}
    ```

=== "Desenvolviment"

    ```python
    {!> ../../../docs_src/settings/custom/development.py!}
    ```

=== "Teste"

    ```python
    {!> ../../../docs_src/settings/custom/testing.py!}
    ```

=== "Produção"

    ```python
    {!> ../../../docs_src/settings/custom/production.py!}
    ```

O que é que acabou de acontecer?

1. Criou-se um `AppSettings` herdado do `Settings` com propriedades comuns entre os ambientes.
2. Criou-se um ficheiro de configuração para cada ambiente, herdando do `AppSettings` base.
3. Criaram-se eventos específicos `on_startup` e `on_shutdown` para cada ambiente.

## Módulo de Configurações

Por defeito, o Lilya procura por uma variável de ambiente chamada `LILYA_SETTINGS_MODULE` para executar as configurações personalizadas.
Se nada for fornecido, ele executará as configurações padrão da aplicação.

=== "Sem LILYA_SETTINGS_MODULE"

    ```shell
    uvicorn src:app --reload

    INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
    INFO:     Started reloader process [28720]
    INFO:     Started server process [28722]
    INFO:     Waiting for application startup.
    INFO:     Application startup complete.
    ```

=== "Com LILYA_SETTINGS_MODULE"

    ```shell
    LILYA_SETTINGS_MODULE=src.configs.production.ProductionSettings uvicorn src:app

    INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
    INFO:     Started reloader process [28720]
    INFO:     Started server process [28722]
    INFO:     Waiting for application startup.
    INFO:     Application startup complete.
    ```

É muito simples, o `LILYA_SETTINGS_MODULE` procura a classe de configurações personalizadas criada para a aplicação
e carrega-a em modo preguiçoso, tornando-a globalmente disponível.

## O settings_module

Esta é uma ótima ferramenta para tornar suas aplicações Lilya 100% independentes e modulares.
Existem casos em que simplesmente se deseja ligar uma aplicação Lilya existente a outra e essa mesma aplicação Lilya já possui configurações e padrões exclusivos.

O `settings_moduke` é um parâmetro disponível em cada instância do `Lilya`, assim como no `ChildLilya`.

### Criar um settings_module

As configurações têm **literalmente o mesmo conceito** que as [Definições](#definicoes-e-a-aplicação), o que significa que cada `settings_module` **deve ser derivado das Definições** ou um `FieldException` é lançado.

A razão pela qual o acima é para manter a integridade da aplicação e das configurações.

```python
{!> ../../../docs_src/applications/settings/settings_config/example2.py !}
```

Isto é simples, literalmente, o Lilya simplifica a forma como pode manipular as definições em cada nível
e mantendo a integridade ao mesmo tempo.

Consulte a [ordem de prioridade](#ordem-de-prioridade) para entender um pouco mais.
### Módulo de configurações como uma string

O Lilya também oferece a possibilidade de importar as configurações via string. Isso significa que pode
literalmente deixar seu código mais limpo e evitar importações em todos os lugares, simplesmente utilizando o caminho do módulo
de importação.

**Exemplo**

Vamos supor que temos um ficheiro de configuração com um nome de classe `AppSettings` localizado dentro de `myapp/configs/settings.py`.

Como importar via string?

```python
{!> ../../../docs_src/applications/settings/settings_config/via_string.py !}
```

## Ordem de prioridade

Existe uma ordem de prioridade na qual o Lilya lê as suas configurações.

Se um `settings_module` for passado para uma instância do Lilya, esse mesmo objecto tem prioridade acima de qualquer outra coisa. Vamos imaginar o seguinte:

* Uma aplicação Lilya com configurações normais.
* Um `ChildLilya` com um conjunto específico de configurações exclusivas.

```python
{!> ../../../docs_src/applications/settings/settings_config/example1.py !}
```

**O que está a acontecer aqui?**

No exemplo acima, nós:

* Criámos um objecto de configurações derivado do `Settings` principal e passámos alguns valores predefinidos.
* Passámos o `ChildLilyaSettings` para a instância do `ChildLilya`.
* Passámos o `ChildLilya` para a aplicação `Lilya`.

Então, como é que a prioridade é aplicada aqui usando o `settings_module`?

* Se nenhum valor de parâmetro (ao instanciar), por exemplo `app_name`, for fornecido, então irá verificar esse mesmo valor dentro do `settings_module`.
* Se o `settings_module` não fornecer um valor para `app_name`, então irá procurar o valor no `LILYA_SETTINGS_MODULE`.
* Se nenhuma variável de ambiente `LILYA_SETTINGS_MODULE` for fornecida, então usará as predefinições do Lilya. [Leia mais sobre isso aqui](#o-settings_module).

Portanto, a ordem de prioridade é a seguinte:

* O valor do parâmetro da instância tem prioridade sobre o `settings_module`.
* O `settings_module` tem prioridade sobre o `LILYA_SETTINGS_MODULE`.
* O `LILYA_SETTINGS_MODULE` é o último a ser verificado.

## Configuração de definições e módulo de configurações do Lilya

A beleza desta abordagem modular é o facto de tornar possível usar **ambas** as abordagens ao mesmo tempo ([ordem de prioridade](#ordem-de-prioridade)).

Vamos usar um exemplo em que:

1. Criamos um objecto principal de definições do Lilya para ser usado pelo `LILYA_SETTINGS_MODULE`.
2. Criamos um `settings_module` para ser usado pela instância do Lilya.
3. Iniciamos a aplicação utilizando ambos.

Vamos também assumir que tem todas as definições dentro de uma directoria `src/configs`.

**Criar uma configuração a ser usada pelo LILYA_SETTINGS_MODULE**

```python title="src/configs/main_settings.py"
{!> ../../../docs_src/applications/settings/settings_config/main_settings.py !}
```

**Criar uma configuração a ser usada pelo settings_module**

```python title="src/configs/app_settings.py"
{!> ../../../docs_src/applications/settings/settings_config/app_settings.py !}
```

**Criar uma instância do Lilya**

```python title="src/app.py"
{!> ../../../docs_src/applications/settings/settings_config/app.py !}
```

Agora podemos iniciar o servidor usando o `AppSettings` como global e o `InstanceSettings` sendo passado
via instanciação. O AppSettings do main_settings.py é usado para chamar a partir da linha de comandos.

```shell
LILYA_SETTINGS_MODULE=src.configs.main_settings.AppSettings uvicorn src:app --reload

INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [28720]
INFO:     Started server process [28722]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

Ótimo! Agora não só utilizamos o `settings_module` e o `LILYA_SETTINGS_MODULE`, mas também os utilizamos ao mesmo tempo!

Confira a [ordem de prioridade](#ordem-de-prioridade) para entender qual valor tem precedência e como o Lilya os lê.

## Parâmetros

Os parâmetros disponíveis dentro de `Settings` podem ser substituídos por quaisquer configurações personalizadas.
## Aceder às definições

Para aceder às definições da aplicação existem diferentes formas:


=== "Dentro do pedido da aplicação"

    ```python
    {!> ../../../docs_src/settings/access/within_app.py!}
    ```

=== "Das configurações globais"

    ```python
    {!> ../../../docs_src/settings/access/global.py!}
    ```

!!! info
    Algumas destas informações podem ter sido mencionadas noutras partes da documentação,
    mas assumimos que as pessoas que as estão a ler podem ter perdido essa mesma informação.

## Ordem de importância

Utilizar as definições para iniciar uma aplicação em vez de fornecer os parâmetros diretamente no momento da
instanciação não significa que um funcionará com o outro.

Quando instancia uma aplicação **ou passa parâmetros diretamente ou usa as definições ou uma combinação de ambos**.

Passar parâmetros no objecto substituirá sempre os valores das definições padrão.

```python
from dataclasses import dataclass

from lilya.conf.global_settings import Settings
from lilya.middleware.httpsredirect import HTTPSRedirectMiddleware
from lilya.middleware import DefineMiddleware


@dataclass
class AppSettings(Settings):
    debug: bool = False

    @property
    def middleware(self) -> List[DefineMiddleware]:
        return [DefineMiddleware(HTTPSRedirectMiddleware)]

```

A aplicação irá:

1. Iniciar com `debug` como `False`.
2. Irá iniciar com um middleware `HTTPSRedirectMiddleware`.

Ao iniciar a aplicação com as configurações acima, garantirá que tenha um `HTTPSRedirectMiddleware` inicial e `debug`
definido com os valores **mas** o que acontece se utilizar as configurações + parâmetros na instanciação?

```python
from lilya.apps import Lilya

app = Lilya(debug=True, middleware=[])
```

A aplicação irá:

1. Iniciar com `debug` como `True`.
2. Irá iniciar sem middlewares personalizados se o `HTTPSRedirectMiddleware` for substituído por `[]`.

Embora tenha sido definido nas configurações para iniciar com `HTTPSRedirectMiddleware` e debug como `False`,
uma vez que passa valores diferentes no momento de instanciar um objecto `Lilya`, esses valores tornar-se-ão os valores a serem usados.

**Declarar parâmetros na instância sempre terá precedência sobre os valores das configurações**.

A razão pela qual deve usar as configurações é porque isso tornará o seu código-fonte mais organizado e mais fácil de manter.

!!! Check
    Quando se passa os valores via instanciação de um objecto Lilya e não via parâmetros, ao aceder os
    valores através de `request.app.settings`, os valores **não estarão nas configurações** pois eles foram passados via
    instanciação da aplicação e não via objecto de configurações. A forma de aceder a esses valores é, por exemplo, via `request.app.debug`
    diretamente.
