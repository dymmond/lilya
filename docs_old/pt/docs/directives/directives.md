# Directivas

O que são essas directivas? Em termos simples, são scripts especiais de linha de comando que executam
trechos de código especiais para o **Lilya**.

## Importante

Antes de ler esta secção, deve familiarizar-se com as formas como o Lilya lida com a descoberta das aplicações.

Os seguintes exemplos e explicações irão utilizar a abordagem [--app e variáveis de ambiente](./discovery.md#environment-variables), mas a [descoberta automática](./discovery.md#auto-discovery) é igualmente válida e funciona da mesma forma.

## Directivas incorporadas do Lilya

Iniciar um projecto pode ser problemático para algumas pessoas, principalmente porque surgem dúvidas sobre a estrutura dos ficheiros
e pastas e como manter a consistência.

Muitas pessoas não se preocupam em executar geradores de código e vão diretos para o próprio design.

!!! Check
    **O Lilya não impõe de forma alguma uma estrutura aplicacional** para qualquer aplicação, mas
    fornece algumas sugestões, mas isso não significa que deva sempre ser assim. Simplesmente serve como uma
    opção.

Atualmente, existem algumas directivas incorporadas.

* [directives](#listar-directivas-disponíveis) - Lista todas as directivas disponíveis.
* [createproject](#criar-projecto) - Usado para gerar uma estrutura básica para um projecto.
* [createapp](#criar-aplicação) - Usado para gerar uma estrutura básica para uma aplicação.
* [createdeploy](#criar-deploy) - Usado para gerar ficheiros para um deploy com docker, nginx, supervisor e gunicorn.
* [show-urls](#mostrar-urls) - Mostra informações sobre a aplicação Lilya.
* [shell](./shell.md) - Inicia o shell interativa do Python para a aplicação Lilya.

### Ajuda

Para obter ajuda sobre qualquer directiva, execute `--help` na frente de cada uma.

Exemplo:

```shell
$ lilya runserver --help
```

## Directivas do Lilya Disponíveis

### Listar Directivas Disponíveis

Esta é a directiva mais simples de executar e lista todas as directivas disponíveis do Lilya
e com a flag `--app` também mostra as directivas disponíveis no seu projecto.

**Apenas directivas do Lilya**

```shell
$ lilya directives
```

**Todas as directivas, incluindo o seu projecto**

```shell
$ lilya --app myproject.main:app directives
```

Ou

```shell
$ export LILYA_DEFAULT_APP=myproject.main:app
$ lilya directives
```

### Criar Projeto

Esta é uma directiva simples que gera uma estrutura de pastas com alguns ficheiros para o projecto Lilya.

#### Parâmetros

* **--with-deployment** - Flag indicando se a geração do projecto deve incluir ficheiros de deploy.

    <sup>Padrão: `False`</sup>

* **--deployment-folder-name** - O nome personalizado da pasta onde os ficheiros de deploy serão colocados se `--with-deployment` for `True`.

    <sup>Padrão: `deployment/`</sup>

* **--with-structure** - Cria um projecto com uma estrutura de pastas e ficheiros específica.
* **-v/--verbosity** - `1` para nenhum e `2` para mostrar todos os ficheiros gerados.

    <sup>Padrão: `1`</sup>

```shell
$ lilya createproject <PROJECT-NAME>
```

A directiva irá gerar uma árvore de ficheiros e pastas com alguns ficheiros pré-populados prontos para serem usados.

!!! Note
    Por defeito, o Lilya irá gerar uma estrutura de projecto simples com o mínimo necessário, a menos que a flag `--with-structure` seja especificada.

**Exemplo**:

Iniciando um projecto com algumas opções padrão e uma estrutura específica.

```shell
$ lilya createproject my_project --with-structure
```

Você deve ter uma pasta chamada `my_project` com uma estrutura semelhante a esta:

```shell
.
├── Taskfile.yaml
├── my_project
│   ├── apps
│   │   └── __init__.py
│   ├── configs
│   │   ├── development
│   │   │   ├── __init__.py
│   │   │   └── settings.py
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   └── testing
│   │       ├── __init__.py
│   │       └── settings.py
│   ├── __init__.py
│   ├── main.py
│   ├── serve.py
│   ├── tests
│   │   ├── __init__.py
│   │   └── test_app.py
│   └── urls.py
└── requirements
    ├── base.txt
    ├── development.txt
    └── testing.txt

```

Muitos ficheiros gerados, certo? Sim, mas na verdade eles são bastante simples, mas vamos falar sobre o que está a acontecer aqui.

* **Taskfile.yaml** - Este é um ficheiro especial fornecido pela directiva que contém alguns comandos úteis para executar o
projecto localmente, por exemplo:
    * `task run` - Inicia o projecto com as configurações de desenvolvimento.
    * `make test` - Executa os testes locais com as configurações de teste.
    * `task clean` - Remove todos os `*.pyc` do projecto.
    * `task requirements` - Instala os requisitos mínimos da pasta `requirements`.

    !!! Info
        Os testes estão a utilizar o [pytest](https://docs.pytest.org/), mas pode trocar por qualquer outro que preferir.

* **serve.py** - Este ficheiro é apenas um wrapper que é chamado pelo `task run` e inicia o desenvolvimento local.
**Isto não deve ser usado em produção**.
* **main.py** - O ficheiro principal que constrói o caminho da aplicação e adiciona-o à `$PYTHONPATH`. Este ficheiro também pode ser
usado para adicionar configurações extra, se necessário.
* **urls.py** - Usado como um *ponto de entrada* para os URLs da aplicação. Este ficheiro já está sendo importado via
**Include** dentro do `main.py`.

#### Apps

##### O que é uma app no contexto do Lilya?

Um app é outra forma de dizer que é um módulo Python que contém código e lógica para a aplicação.

Como mencionado anteriormente, isto é apenas uma sugestão e de forma alguma constitui a única maneira de
construir aplicações Lilya.

A pasta `apps` é uma forma que pode ser usada para **isolar** as APIs do restante da estrutura. Esta pasta já está
adicionada no caminho do Python via `main.py`.

Pode simplesmente ignorar esta pasta ou usá-la como pretendido, **nada é obrigatório**, acreditamos apenas que, além de um
código limpo, uma estrutura limpa torna tudo mais agradável de trabalhar e manter.

> Então, está a dizer que podemos usar os apps para isolar as APIs e podemos ignorá-los ou usá-los.
Também existe alguma outra directiva que sugere como criar uma app, apenas no caso de querermos?

**Na verdade, sim!** Também pode usar a directiva [createapp](#criar-aplicação) para gerar uma estrutura básica para uma app.

### Criar Aplicação

Esta é outra directiva que permite gerar uma estrutura básica para uma possível app a ser usada no Lilya.

#### Parâmetros

* **-v/--verbosity** - `1` para nenhum e `2` para exibir todos os ficheiros gerados.

    <sup>Padrão: `1`</sup>

```shell
$ lilya createapp <APP-NAME>
```

**Exemplo**:

Usando o exemplo anterior de [criar um projecto](#criar-projecto), vamos usar o `my_project` já criado.

```shell
$ cd my_project/apps/
$ lilya createapp accounts
```

Feve ter uma pasta chamada `accounts` com uma estrutura semelhante a esta:

{!> ../../../docs_src/_shared/app_struct_example.md !}

Como pode ver, `my_project/apps` contém uma app chamado `accounts`.

Por defeito, o `createapp` gera um módulo Python com um submódulo `v1` que contém:

* **schemas.py** - Ficheiro vazio com uma simples importação de `BaseModel` do Pydantic e onde você pode colocar qualquer,
como o próprio import sugere, modelo Pydantic para ser usado com o `accounts/v1`.
* **urls.py** - Pode colocar os URLs das views do seu `accounts/v1`.
* **controllers.py** - Você pode colocar todos os *handlers* e views do `accounts/v1`.

Um ficheiro de **tests** também é gerado sugerindo que também pode adicionar alguns testes específicos da aplicação lá.

!!! Check
    Usar uma versão como `v1` deixa claro qual é versão das APIs que deve ser desenvolvida dentro do mesmo
    módulo e por esse motivo um `v1` padrão é gerado, mas novamente, nada é definitivo e é livre
    para simplesmente ignorar isto.

### Após a geração

Depois que o projecto e as apps serem gerados, a execução do `task run` lançará uma excepção `ImproperlyConfigured`. Isto
acontece porque o `urls.py` espera ser preenchido com os detalhes da aplicação.

### Exemplo

Vamos fazer um exemplo usando exatamente o que geramos anteriormente e colocar o aplicação em funcionamento.

**A estrutura atual**:

{!> ../../../docs_src/_shared/app_struct_example.md !}

O que vamos fazer?

* Adicionar uma *view* às accounts.
* Adicionar o caminho para as `urls` das accounts.
* Adicionar as urls das accounts às urls da aplicação.
* Iniciar a aplicação.

#### Criar a view

```python title="my_project/apps/accounts/v1/controllers.py"
{!> ../../../docs_src/management/views.py !}
```

Crie uma view para retornar a mensagem `Welcome home!`.

#### Adicionar a view às urls

Agora é hora de adicionar a view recém-criada às urls das accounts.

```python title="my_project/apps/accounts/v1/urls.py"
{!> ../../../docs_src/management/urls.py !}
```

#### Adicionar as urls das accounts às urls do aplicação

Agora que criamos as views e as urls para as accounts, é hora de adicionar as accounts às urls da aplicação.

Vamos atualizar o `my_project/urls.py`.

```python title="my_project/urls.py"
{!> ../../../docs_src/management/app_urls.py !}
```

E é isto! A aplicação está montado e agora pode [iniciar a aplicação](#iniciar-o-aplicação).

### Iniciar a aplicação

Lembre-se de que um `Taskfile.yaml` também foi gerado? Vamos usá-lo para iniciar a aplicação.

```shell
task run
```

O que esse comando está a fazer na verdade é:

```shell
LILYA_SETTINGS_MODULE=my_project.configs.development.settings.DevelopmentAppSettings python -m my_project.serve
```

Se quiser usar outras [configurações](../settings.md#configurações-personalizadas), basta atualizar o comando para
executar com suas configurações personalizadas.

Assim que a aplicação iniciar, deve ter um *output* na consola semelhante a esta:

```shell
INFO:     Uvicorn running on http://localhost:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [4623] using WatchFiles
INFO:     Started server process [4625]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### Ficheiros de teste gerados automaticamente

Os ficheiros de teste gerados estão usando o TestClient, portanto, certifique-se de executar:

```shell
$ pip install lilya[full]
```

Ou você pode saltar esta etapa se não quiser usar o TestClient.

### Criar Deploy

Esta é outra directiva que permite gerar uma estrutura básica para um deploy usando nginx, supervisor, gunicorn e docker.

!!! Note
    Isso gera ficheiros prontos contendo as informações mínimas necessárias para acelerar o processo de deploy
    e pode/devem ser adaptados às suas necessidades, mas pelo menos 80% das configurações já estão
    preparadas.

    A imagem `Dockerfile` vem com a versão mínima do Python 3.12. É recomendado atualizar de acordo
    se tiver alguma restrição.

Existem duas maneiras de gerar os deploys. Uma com o [createproject](#criar-projecto) e fornecendo
as flags necessárias e a outra de forma isolada.

**Esta directiva é considerada de forma isolada**.

#### Parâmetros

* **--deployment-folder-name** - O nome personalizado da pasta onde os ficheiros serão colocados.

    <sup>Padrão: `deployment/`</sup>

* **-v/--verbosity** - `1` para nenhum e `2` para exibir todos os ficheiros gerados.

    <sup>Padrão: `1`</sup>

A execução e sintaxe padrão são as seguintes:

```shell
$ lilya createdeploy <PROJECT-NAME>
```

**Exemplo**:

Usando nosso exemplo anterior de [criar projecto](#criar-projecto), vamos usar o `my_project` já criado.

```shell
$ cd my_project/
$ lilya createdeploy my_project
```

Deve ter uma pasta chamada `deployment` com uma estrutura semelhante a esta:

{!> ../../../docs_src/_shared/deployment_struct_example.md !}

Como pode ver, todos os ficheiros mínimos para o seu projecto são gerados dentro de uma pasta padrão `deployment/`
e prontos para serem usados, economizando uma quantidade enorme de tempo.

Mas e se quiser fornecer um nome diferente para a pasta de deploy em vez de `deployment/`?

Bem, graças ao parâmetro `--deployment-folder-name`, pode especificar o nome da pasta e
isso também será refletido nos ficheiros.

**Exemplo**:

Vamos usar `my_project` como exemplo e chamar a pasta de `deploy` em vez de `deployment`.

```shell
$ lilya createdeploy my_project --deployment-folder-name deploy
```

Depois que a directiva for executada, deve ter uma pasta chamada `deploy` com uma estrutura semelhante a esta:

{!> ../../../docs_src/_shared/deploy_struct_example.md !}

#### Executar o Dockerfile

Como tudo já está fornecido e as suas alterações nos ficheiros são refletidas, por exemplo, ao garantir que os requisitos
são instalados dentro da imagem Docker, pode executar a construção da imagem Docker directamente a partir da raiz do projecto.

**Exemplo**

Usando o exemplo `myproject`, seria algo assim:

```shell
$ docker build -t myorg/myproject:latest -f deployment/docker/Dockerfile .
```

!!! Tip
    Se não está familiarizado com o Docker, é altamente recomendado
    [ler a documentação oficial](https://docs.docker.com/) e de se familiarizar com ele.

Isto deve iniciar todo o processo do `Dockerfile` e instalar tudo conforme necessário.

!!! Warning
    Se não deseja os mesmos locais para os ficheiros gerados, pode simplesmente movê-los para qualquer
    lugar à sua escolha e atualizar os ficheiros de acordo para refletir suas configurações personalizadas.

### Mostrar URLs

Esta é outra aplicação integrada do Lilya e serve para mostrar as informações sobre as
URLs da sua aplicação via linha de comandos.

Este comando pode ser executado da seguinte forma:

!!! Tip
    O Lilya, antes de tentar qualquer coisa, tentará percorrer algumas configurações padrão e tentar encontrar uma aplicação Lilya
    automaticamente. Se não for encontrado, pode seguir as próximas instruções.

**Usando o parâmetro --app**

```shell
$ lilya --app myproject.main:app show-urls
```

**Usando a variável de ambiente LILYA_DEFAULT_APP já exportada**:

```shell
$ lilya myproject.main:app show-urls
```

### Runserver

Esta é uma directiva extremamente poderosa e **deve ser usada apenas para fins de desenvolvimento**.

Esta directiva ajuda a iniciar o desenvolvimento local de uma maneira simples, muito semelhante ao
`runserver` do Django, na verdade, como foi inspirado nele, o mesmo nome foi mantido.

!!! Perigo
    Para usar esta directiva, o `uvicorn` deve estar instalado.

#### Parâmetros

* **-p/--port** - O porto em que o servidor deve iniciar.

    <sup>Padrão: `8000`</sup>

* **-r/--reload** - Recarregar o servidor quando houver alterações nos ficheiros.

    <sup>Padrão: `True`</sup>

* **--host** - Host do servidor. Tipicamente `localhost`.

    <sup>Padrão: `localhost`</sup>

* **--debug** - Iniciar o aplicação no modo de depuração.

    <sup>Padrão: `True`</sup>

* **--log-level** - Nível de log que o uvicorn deve usar.

    <sup>Padrão: `debug`</sup>

* **--lifespan** - Habilitar eventos de ciclo de vida. Opções: `on`, `off`, `auto`.

    <sup>Padrão: `on`</sup>

* **--settings** - Iniciar o servidor com configurações específicas. Esta é uma alternativa ao
modo de iniciar com [LILYA_SETTINGS_MODULE][settings_module].

    <sup>Padrão: `None`</sup>

##### Como usar

O Runserver possui algumas configurações padrão que são tipicamente usadas para desenvolvimento, mas vamos executar
algumas das opções para ver como ficaria.

!!! Warning
    Os exemplos e explicações a seguir usarão a abordagem de [descoberta automática](./discovery.md#auto-discovery),
    mas o uso de [--app e variáveis de ambiente](./discovery.md#environment-variables)
    é igualmente válido e funciona da mesma maneira.

###### Executar em uma porta diferente

```shell
$ lilya runserver -p 8001
```

###### Executar em um host diferente

Embora ainda seja localhost, executamos diretamente com o IP.

```shell
$ lilya runserver --host 127.0.0.1
```

###### Executar com um ciclo de vida diferente

```shell
$ lilya runserver --lifespan auto
```

###### Executar com configurações diferentes

Como mencionado anteriormente, esta é uma alternativa ao [LILYA_SETTINGS_MODULE][settings_module]
e **deve ser usada apenas para fins de desenvolvimento**.

Use um ou outro.

Vamos assumir a seguinte estrutura de ficheiros e pastas que conterão configurações diferentes.

```shell hl_lines="9 10 13" title="myproject"
.
├── Taskfile.yaml
└── src
    ├── __init__.py
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

Como pode ver, temos três tipos diferentes de configurações:

* **development** (desenvolvimento)
* **testing** (teste)
* **production settings** (configurações de produção)

**Executar com configurações de desenvolvimento**

```shell
$ lilya runserver --settings src.configs.development.settings.DevelopmentAppSettings
```

Executar com [LILYA_SETTINGS_MODULE][settings_module] seria:

```shell
$ LILYA_SETTINGS_MODULE=src.configs.development.settings.DevelopmentAppSettings lilya runserver
```

**Executar com configurações de teste**

```shell
$ lilya runserver --settings src.configs.testing.settings.TestingAppSettings
```

Executar com [LILYA_SETTINGS_MODULE][settings_module] seria:

```shell
$ LILYA_SETTINGS_MODULE=src.configs.testing.settings.TestingAppSettings lilya runserver
```

**Executar com configurações de produção**

```shell
$ lilya runserver --settings src.configs.settings.AppSettings
```

Executar com [LILYA_SETTINGS_MODULE][settings_module] seria:

```shell
$ LILYA_SETTINGS_MODULE=src.configs.settings.AppSettings lilya runserver
```

[settings_module]: ../settings.md#settings-config-and-lilya-settings-module
