# Cliente Lilya

Lilya traz um cliente interno **opcional** que oferece algumas facilidades quando está em desenvolvimento
ou até mesmo quando deseja executar alguns *scripts* personalizados com a utilização de [diretivas](./directives/directives.md).

Diretivas são pedaços especiais de código e lógica que podem ser executados em qualquer ambiente e de forma isolada. Veja como uma espécie de centro de comando.

Como o **cliente Lilya é opcional**, isso também significa que para usá-lo **precisa de instalar** os requisitos.

```shell
$ pip install lilya[cli]
```

Lilya utiliza a biblioteca `click` como suporte.

## Como funciona

Bem, como qualquer cliente Python normal, a melhor maneira de ver quais opções estão disponíveis é executar:

```shell
$ lilya --help
```

Isso mostrará as diretivas internas às quais **todos projetos Lilya têm acesso**.

Ao executar, deve mostrar uma mensagem parecida com a seguinte:

```shell
Usage: lilya [OPTIONS] COMMAND [ARGS]...

  Lilya command line tool allowing to run Lilya native directives or project
  unique and specific directives by passing the `-n` parameter.

  How to run Lilya native: `lilya createproject <NAME>`. Or any other Lilya
  native command.

      Example: `lilya createproject myapp`

  How to run custom directives: `lilya --app <APP-LOCATION> run -n <DIRECTIVE
  NAME> <ARGS>`.

      Example: `lilya --app myapp:app run -n createsuperuser`

Options:
  --app TEXT  Module path to the application to generate the migrations. In a
              module:path format.
  --n TEXT    The directive name to run.
  --help      Show this message and exit.

Commands:
  createapp         Creates the scaffold of an application
  createdeployment  Generates the scaffold for the deployment of a Lilya...
  createproject     Creates the scaffold of a project.
  directives        Lists the available directives
  run               Runs every single custom directive in the system.
  runserver         Starts the Lilya development server.
  shell             Starts an interactive ipython shell with all the...
  show-urls         Shows the information regarding the urls of a given...
```

Os `commands` são simples comandos que pode utilizar para interagir com o cliente. Para aceder as opções de cada `command` so precisa de:

**Exemplo**

```shell
Usage: lilya createproject [OPTIONS] NAME

  Creates the scaffold of a project.

  How to run: `lilya createproject <NAME>`

  Example: `lilya createproject myproject`

Options:
  -v, --verbosity INTEGER        Displays the files generated.
  --with-structure               Creates a project with a given structure of
                                 folders and files.
  --deployment-folder-name TEXT  The name of the folder for the deployment
                                 files.  [default: deployment]
  --with-deployment              Creates a project with base deployment files.
  --help                         Show this message and exit.
```

Veja como tirar proveito das [diretivas](./directives/directives.md) do Lilya.
