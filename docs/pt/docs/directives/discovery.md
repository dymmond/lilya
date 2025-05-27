# Descoberta da Aplicação

Lilya possui várias maneiras diferentes de perceber os comandos, uma delas é através de [variáveis de ambiente](#variáveis-de-ambiente) e outra é através da [descoberta automática](#descoberta-automática).

## Descoberta Automática

Se está familiarizado com outras frameworks como Django, com certeza está familiarizado com a forma como eles utilizam o `manage.py` para executar internamente todos os comandos.

O Lilya não possui um `manage.py` e não é opinativo nesse nível, pois não é um monólito (a menos que **o desenhe para ser**).

Embora não tenha o mesmo nível, o Lilya faz um trabalho semelhante ao ter "um palpite" do que deve ser e gera um erro se não for encontrado ou se nenhuma [variável de ambiente ou --app](#variáveis-de-ambiente) for fornecida.

**A descoberta da aplicação funciona como uma alternativa para fornecer o `--app` ou uma variável de ambiente `LILYA_DEFAULT_APP`.**

Então, o que é que isso significa?

Isto significa que se **não fornecer um --app ou um LILYA_DEFAULT_APP**, o Lilya tentará encontrar a aplicação automaticamente.

Vamos ver um exemplo prático do que isso significa.

Imagine a seguinte estrutura de pastas e ficheiros:

```shell hl_lines="20" title="myproject"
.
├── Taskfile.yaml
└── myproject
    ├── __init__.py
    ├── apps
    │   ├── accounts
    │   │   ├── directives
    │   │   │   ├── __init__.py
    │   │   │   └── operations
    │   │   │       └── __init__.py
    ├── configs
    │   ├── __init__.py
    │   ├── development
    │   │   ├── __init__.py
    │   │   └── settings.py
    │   ├── settings.py
    │   └── testing
    │       ├── __init__.py
    │       └── settings.py
    ├── main.py
    ├── tests
    │   ├── __init__.py
    │   └── test_app.py
    └── urls.py
```

A estrutura acima do `myproject` possui muitos ficheiros e o destacado é o que contém o objecto da aplicação `Lilya`.

### Como funciona?

Quando nenhum `--app` ou nenhuma variável de ambiente `LILYA_DEFAULT_APP` é fornecida, o Lilya irá **procurar automaticamente por**:

* O diretório atual onde a directiva está a ser chamada contém um ficheiro chamado:
    * **main.py**
    * **app.py**
    * **application.py**

    !!! Warning
        **Se nenhum desses ficheiros for encontrado**, o Lilya irá verificar **apenas para os primeiros nós filhos** e repetir o mesmo processo. Se nenhum ficheiro for encontrado, lançará uma excepção `EnvError`.

* Uma vez que um desses ficheiros é encontrado, o Lilya analisará o tipo de objectos contidos no módulo e verificará se algum deles é um tipo válido `Lilya` e o retornará.

* Se o Lilya entender que nenhum desses objectos é do tipo `Lilya` (ou subclasses), fará uma última tentativa e tentará encontrar declarações de função específicas:
    * **get_application()**
    * **get_app()**

Esta é a maneira como o Lilya pode `descobrir automaticamente` a aplicação.

!!! Note
    O Flask possui um padrão semelhante para as funções chamadas `create_app`. O Lilya não usa o
    `create_app`, em vez disso, usa o `get_application` ou `get_app` como um padrão, pois parece mais limpo.

## Variáveis de Ambiente

Ao usar algumas das directivas personalizadas ou directivas internas com este método, o Lilya
**espera que pelo menos uma variável de ambiente esteja presente**.

* **LILYA_DEFAULT_APP** - A aplicação Lilya para executar as directivas.

O motivo para isto é porque cada aplicação Lilya pode diferir em estrutura e design.
Como o Lilya não é opinativo em relação à forma como deve montar a aplicação, precisa saber
**pelo menos onde o ponto de entrada será**.

Além disso, oferece um design limpo para quando é necessário ir para produção, pois o procedimento é
muito provavelmente feito usando variáveis de ambiente.

Então, para economizar tempo, pode simplesmente fazer:

```shell
$ export LILYA_DEFAULT_APP=myproject.main:app
```

Ou qualquer localização que tenha.

Alternativamente, pode simplesmente passar `--app` como um parâmetro com a localização da sua aplicação.

Exemplo:

```shell
$ lilya --app myproject.main:app show-urls
```

## Como usar e quando usar

Anteriormente, foi utilizada uma estrutura de pastas como exemplo e, em seguida, uma explicação de como o Lilya entenderia a descoberta automática, mas na prática,
como é que isso funcionaria?

Vamos usar algumas das directivas internas principais do Lilya e executá-las nessa mesma estrutura.

**Isto aplica-se a qualquer [directiva](./directives.md) ou [directiva personalizada](./custom-directives.md)**.

Vamos ver novamente a estrutura, caso já se tenha esquecido.

```shell hl_lines="20" title="myproject"
.
├── Taskfile.yaml
└── src
    ├── __init__.py
    ├── apps
    │   ├── accounts
    │   │   ├── directives
    │   │   │   ├── __init__.py
    │   │   │   └── operations
    │   │   │       └── __init__.py
    ├── configs
    │   ├── __init__.py
    │   ├── development
    │   │   ├── __init__.py
    │   │   └── settings.py
    │   ├── settings.py
    │   └── testing
    │       ├── __init__.py
    │       └── settings.py
    ├── main.py
    ├── tests
    │   ├── __init__.py
    │   └── test_app.py
    └── urls.py
```

O `main.py` é o ficheiro que contém a aplicação `Lilya`. Um ficheiro que poderia ser assim:

```python title="myproject/src/main.py"
{!> ../../../docs_src/directives/discover.py !}
```

Este é um exemplo simples com dois endpoints, pode fazer como desejar com os padrões que desejar
adicionar e com qualquer estrutura desejada.

Agora vamos executar as seguintes directivas usando a [descoberta automática](#descoberta-automática)
e o [--app ou LILYA_DEFAULT_APP](#variáveis-de-ambiente):

* **directives** - Lista todas as directivas disponíveis do projeto.
* **runserver** - Inicia o servidor de desenvolvimento.

Também executaremos as directivas dentro de `myproject`.

**Pode ver mais informações sobre essas [directivas](./directives.md), incluindo parâmetros, na próxima secção.**

### Usando a descoberta automática

#### directives

##### Usando a descoberta automática

```shell
$ lilya directives
```

Sim! Apenas isso e porque o `--app` ou um `LILYA_DEFAULT_APP` foi fornecido, o Lilya despoletou a
descoberta automática da aplicação.

Como a aplicação está dentro de `src/main.py`, ela será automaticamente descoberta pelo Lilya, pois
seguiu o [padrão de descoberta](#como-funciona).

##### Usando o --app ou LILYA_DEFAULT_APP

Esta é a outra maneira de informar ao Lilya onde encontrar a aplicação. Como a aplicação está
dentro de `src/main.py`, precisamos fornecer a localização adequada no formato `<module>:<app>`.

###### --app

Com a flag `--app`.

```shell
$ lilya --app src.main:app directives
```

###### LILYA_DEFAULT_APP

Com o `LILYA_DEFAULT_APP`.

Exporte a variável de ambiente primeiro:

```shell
$ export LILYA_DEFAULT_APP=src.main:app
```

E então execute:

```shell
$ lilya directives
```

#### runserver

Agora isto é uma jóia! Esta directiva é especial e **deve ser usada apenas para desenvolvimento**.
Pode ver [mais detalhes](./directives.md#runserver) de como usá-la e os parâmetros correspondentes.

É hora de executar esta directiva.

!!! Note
    Para fins de desenvolvimento, o Lilya usa o `uvicorn`. Se não o tiver instalado, execute
    `pip install uvicorn`.

##### Usando a descoberta automática

```shell
$ lilya runserver
```

Novamente, mesmo princípio que antes, porque o `--app` ou um `LILYA_DEFAULT_APP` foi fornecido,
o Lilya despoletou a descoberta automática da aplicação.

##### Usando o --app ou LILYA_DEFAULT_APP

###### --app

Com a flag `--app`.

```shell
$ lilya --app src.main:app runserver
```

###### LILYA_DEFAULT_APP

Com o `LILYA_DEFAULT_APP`.

Exporte a variável de ambiente primeiro:

```shell
$ export LILYA_DEFAULT_APP=src.main:app
```

E então execute:

```shell
$ lilya runserver
```
