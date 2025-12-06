# Directivas Personalizadas

Ter [directivas embutidas](./directives.md) do Lilya é ótimo, pois oferece muitas facilidades para o seu projecto, mas ter **directivas personalizadas** é o que realmente potencializa a sua aplicação e a eleva.

## Importante

Antes de ler esta secção, deve familiarizar-se com as formas como o Lilya lida com a descoberta das aplicações.

Os seguintes exemplos e explicações irão utilizar a abordagem [--app e variáveis de ambiente](./discovery.md#environment-variables), mas a [descoberta automática](./discovery.md#auto-discovery) é igualmente válida e funciona da mesma forma.

## O que é uma directiva personalizada?

Antes de entrarmos nisso, vamos voltar às raízes do Python.

O Python era e ainda é amplamente utilizado como uma linguagem de script. Os scripts são pedaços isolados de código e lógica que podem ser executados em qualquer máquina que tenha o Python instalado e executar sem muitos problemas ou obstáculos.

Bastante simples, certo?

Então, o que é isso tem a ver com directivas? Bem, as directivas seguem o mesmo princípio, mas aplicado ao seu próprio projecto. E se pudesse criar os seus próprios scripts estruturados dentro do seu projecto diretamente? E se pudesse construir pedaços de lógica dependentes ou independentes que pudessem ser executados usando os recursos da sua própria aplicação Lilya?

Isso é o que é uma directiva.

!!! Tip
    Se está familiarizado com os comandos de gestão do Django, as directivas do Lilya seguem o mesmo princípio. Há um [excelente artigo](https://simpleisbetterthancomplex.com/tutorial/2018/08/27/how-to-create-custom-django-management-commands.html) sobre isso se se quiser familiarizar.

### Exemplos

Imagine que precisa criar uma base de dados que conterá todas as informações sobre acessos de utilizadores específicos e gerirá as funções da sua aplicação.

Agora, uma vez que essa base de dados é criada com sua aplicação, geralmente precisaria se conectar ao seu servidor de produção e configurar manualmente um utilizador ou executar um script ou comando específico para criar o mesmo superutilizador. Isso pode ser demorado e propenso a erros, certo?

Pode usar uma [directiva](#directive) para fazer esse mesmo trabalho por si.

Ou e se precisar criar operações específicas para serem executadas em segundo plano por algumas operações que não requerem APIs, por exemplo, atualizar a função de um utilizador? As directivas resolvem esse problema também.

Há um mundo de possibilidades do que se pode fazer com as directivas.

## Directiva

Esta é a classe principal para **cada directiva personalizada** que deseja implementar. Este é um objecto especial com algumas configurações padrão que pode usar.

### Parâmetros

* **--directive** - O nome da directiva (o ficheiro onde a Directiva foi criada).
Verifique [listar todas as directivas](./directives.md#listar-directivas-disponíveis) para obter mais detalhes sobre como obter os nomes.

### Como executar

A sintaxe é muito simples para uma directiva personalizada:

**Com o parâmetro --app**

```shell
$ lilya --app <LOCALIZAÇÃO> run --directive <DIRECTIVE-NAME> <OPTIONS>
```

Exemplo:

```shell
lilya --app myproject.main:app run --directive mydirective --name lilya
```

**Com a variável de ambiente LILYA_DEFAULT_APP definida**

```shell
$ export LILYA_DEFAULT_APP=myproject.main:app
$ lilya run --directive <DIRECTIVE-NAME> <OPTIONS>
```

Exemplo:

```shell
$ export LILYA_DEFAULT_APP=myproject.main:app
$ lilya run --directive mydirective --name lilya
```

O `run --directive` está **sempre** à espera do nome do ficheiro da directiva.

Por exemplo, criou um ficheiro `createsuperuser.py` com a lógica da `Directiva`. O parâmetro `--directive`
será `run --directive createsuperuser`.

Exemplo:

```shell
$ export LILYA_DEFAULT_APP=myproject.main:app
$ lilya run --directive createsuperuser --email example@lilya.dev
```

### Como criar uma directiva

Para criar uma directiva, **deve herdar da classe BaseDirective** e o nome do objecto **deve-se chamar `Directive`**.

```python
from lilya.cli.base import BaseDirective
```

**Crie a classe Directiva**

```python hl_lines="4 7"
{!> ../../../docs_src/directives/base.py !}
```

Todas as directivas personalizadas criadas **devem ser chamadas de Directive** e **deve herdar** da classe
`BaseDirective`.

Internamente, o `lilya` procura por um objecto `Directive` e verifica se é uma subclasse de `BaseDirective`.
Se uma dessas condições falhar, lançará um `DirectiveError`.

### Onde as directivas devem ser colocadas?

Todas as directivas personalizadas criadas **devem estar** dentro de um módulo `directives/operations` para
serem descobertas.

O local para as `directives/operations` pode ser em qualquer lugar da aplicação e também pode ter **mais do que uma**.

Exemplo:

```shell hl_lines="10 16 22 36"
.
├── Taskfile.yaml
└── myproject
    ├── __init__.py
    ├── apps
    │   ├── accounts
    │   │   ├── directives
    │   │   │   ├── __init__.py
    │   │   │   └── operations
    │   │   │       ├── createsuperuser.py
    │   │   │       └── __init__.py
    │   ├── payroll
    │   │   ├── directives
    │   │   │   ├── __init__.py
    │   │   │   └── operations
    │   │   │       ├── run_payroll.py
    │   │   │       └── __init__.py
    │   ├── products
    │   │   ├── directives
    │   │   │   ├── __init__.py
    │   │   │   └── operations
    │   │   │       ├── createproduct.py
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
    ├── directives
    │   ├── __init__.py
    │   └── operations
    │       ├── db_shell.py
    │       └── __init__.py
    ├── main.py
    ├── serve.py
    ├── tests
    │   ├── __init__.py
    │   └── test_app.py
    └── urls.py
```

Como pode ver no exemplo anterior, temos quatro directivas:

* **createsuperuser** - Dentro de `accounts/directives/operations`.
* **run_payroll** - Dentro de `payroll/directives/operations`.
* **createproduct** - Dentro de `products/directives/operations`.
* **db_shell** - Dentro de `./directives/operations`.

Todas elas, não importa onde coloque a directiva, estão dentro de um **directives/operations** onde
o lilya vai sempre procurar.

### Funções da directiva

#### handle()

A lógica da `Directiva` é implementada dentro de uma função `handle` que pode ser `síncrona` ou
`assíncrona`.

Ao chamar uma `Directiva`, o `lilya` executará o `handle()` e executará toda a lógica.

=== "Síncrona"

    ```python hl_lines="15"
    {!> ../../../docs_src/directives/sync_handler.py !}
    ```

=== "Assíncrona"

    ```python hl_lines="15"
    {!> ../../../docs_src/directives/async_handler.py !}
    ```

Como pode ver, as Directivas do Lilya também permitem funções `assíncronas` e `síncronas`. Isto pode ser
particularmente útil quando precisa executar tarefas específicas no modo assíncrono, por exemplo.

#### add_arguments()

Este é o local onde adiciona qualquer argumento necessário para executar sua directiva personalizada. Os argumentos
são argumentos relacionados ao `argparse`, portanto, a sintaxe deve ser familiar.

```python
{!> ../../../docs_src/directives/arguments.py !}
```

Como pode ver, a Directiva tem cinco parâmetros e todos eles são obrigatórios.

```shell
lilya --app teste.main:app run --directive mydirective --first-name Lilya --last-name Toolkit --email example@lilya.dev --username lilya --password lilya

```

## Ajuda

Existem duas opções de ajuda para as directivas. Uma quando executa o executor do lilya (run) e
outra para a `directive` em si.

### --help

Este comando **é usado apenas para a ajuda do executor**, por exemplo:

```shell
$ lilya run --help
```

### -h

Esta opção é usada para acessar a ajuda da `directive` e não do `run`.

```shell
$ lilya run --directive mydirective -h
```

### Observações

A **única maneira de ver a ajuda de uma directiva** é através de `-h`.

Se o `--help` for usado, ele mostrará apenas a ajuda do `run` e não da `directive` em si.

## Ordem de prioridade

**Isso é muito importante perceber**.

O que acontece se tivermos duas directivas personalizadas com o mesmo nome?

Vamos usar a seguinte estrutura como exemplo:

```shell hl_lines="10 32"
.
├── Taskfile.yaml
└── myproject
    ├── __init__.py
    ├── apps
    │   ├── accounts
    │   │   ├── directives
    │   │   │   ├── __init__.py
    │   │   │   └── operations
    │   │   │       ├── createsuperuser.py
    │   │   │       └── __init__.py
    │   │   ├── __init__.py
    │   │   ├── models.py
    │   │   ├── tests.py
    │   │   └── v1
    │   │       ├── __init__.py
    │   │       ├── schemas.py
    │   │       ├── urls.py
    │   │       └── controllers.py
    ├── configs
    │   ├── __init__.py
    │   ├── development
    │   │   ├── __init__.py
    │   │   └── settings.py
    │   ├── settings.py
    │   └── testing
    │       ├── __init__.py
    │       └── settings.py
    ├── directives
    │   ├── __init__.py
    │   └── operations
    │       ├── createsuperuser.py
    │       └── __init__.py
    ├── main.py
    ├── serve.py
    ├── tests
    │   ├── __init__.py
    │   └── test_app.py
    └── urls.py
```

Este exemplo está a simular uma estrutura de um projecto Lilya com
**duas directivas personalizadas com o mesmo nome**.

A primeira directiva está dentro de `./directives/operations/` e a segunda dentro de
`./apps/accounts/directives/operations`.

As directivas do Lilya funcionam com base no princípio de **Primeiro Encontrado, Primeiro Executado**, o que significa que se tiver
duas directivas personalizadas com o mesmo nome, o lilya irá
**executar a primeira directiva encontrada com aquele nome específico**.

Noutras palavras, se quiser executar o `createsuperuser` do `accounts`, a primeira directiva encontrada
dentro de `./directives/operations/` **deve ter um nome diferente** ou então será executada
em vez da pretendida em `accounts`.

## Execução

As directivas do Lilya usam os mesmos eventos passados na aplicação.

Por exemplo, se deseja executar operações de base de dados e as conecções de base de dados devem ser
estabelecidas antecipadamente, pode fazer de duas maneiras:

* Usar os eventos de [Lifespan](../lifespan.md) e as directivas os utilizarão.
* Estabelecer as conecções (abrir e fechar) dentro da Directiva diretamente.

O [exemplo prático](#um-exemplo-prático) usa os [eventos de lifespan](../lifespan.md) para
executar as operações. Desta forma, só precisa de um lugar para gerir os eventos da aplicação necessários.

## Um exemplo prático

Vamos executar um exemplo de uma directiva personalizada para a sua aplicação. Como mencionamos o
`createsuperuser` com frequência, vamos criar essa mesma directiva e aplicá-la à nossa aplicação Lilya.

Para este exemplo, usaremos o [Saffier][saffier], pois isso permitirá fazer uma directiva completa de ponta à ponta
usando a abordagem `assíncrona`.

Este exemplo é muito simples.

Para produção, deve ter seus modelos num local dedicado e suas configurações de `registry`
e `database` nalgum lugar do seu `settings` onde possa aceder em qualquer lugar do código por meio
das [configurações do lilya](../settings.md), por exemplo.

P.S.: Para a estratégia de registro e base de dados com [saffier][saffier], é bom ler
as [dicas e truques](https://saffier.tarsild.io/tips-and-tricks/) com saffier.

O design fica ao seu critério.

O que vamos criar:

* **myproject/main/main.py** - O ponto de entrada para nossa aplicação Lilya
* **createsuperuser** - Nossa directiva.

No final, simplesmente executamos a directiva.

Também usaremos o [Saffier](https://saffier.tarsild.io) para os modelos do base de dados, pois isso tornará o exemplo mais simples.

### O ponto de entrada da aplicação

```python title="myproject/main.py"
{!> ../../../docs_src/directives/example/app.py !}
```

A string de conecção deve ser substituída pelo que for adequado para si.

### O createsuperuser

Agora é hora de criar a directiva `createsuperuser`. Como mencionado [acima](#onde-as-directivas-devem-ser-colocadas),
a directiva deve estar dentro de um módulo `directives/operations`.

```python title="myproject/directives/operations/createsuperuser.py"
{!> ../../../docs_src/directives/example/createsuperuser.py !}
```

E isso deve ser tudo. Agora temos um `createsuperuser` e uma aplicação e agora podemos executar no terminal:

**Usando a descoberta automática**

```shell
$ lilya run --directive createsuperuser --first-name Lilya --last-name Framework --email example@lilya.dev --username lilya --password lilya
```

**Usando o --app ou LILYA_DEFAULT_APP**

```shell
$ lilya --app myproject.main:app run --directive createsuperuser --first-name Lilya --last-name Framework --email example@lilya.dev --username lilya --password lilya
```

Ou

```shell
$ export LILYA_DEFAULT_APP=myproject.main:app
$ lilya run --directive createsuperuser --first-name Lilya --last-name Framework --email example@lilya.dev --username lilya --password lilya
```

Após a execução do comando, deverá ver o superutilizador criado na sua base de dados.

[saffier]: https://saffier.tarsild.io
