# Lilya Client

Lilya comes with an **optional** internal client that offers some niceties for when you are
in development mode or even when you want to run some custom *scripts* live with the use of
[directives](./directives/directives.md).

Directives are special pieces of code and logic that can be executed in any environment and in
isolation. See it as come sort of command center.

Since **Lilya client is optional**, that also means to use it **you will need to install** the
requirements.

```shell
$ pip install lilya[cli]
```

Lilya uses the `click` library for its own purposes.

## How does it work

Well, like any normal Python client, to access the best way of seeing what options are available
to you is by running:

```shell
$ lilya --help
```

This display the internal directives that **every Lilya project has access to**.

When running, it should display a message similar to this following:

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
              module:path formatyping.
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
  show_urls         Shows the information regarding the urls of a given...
```

The `commands` are the simple commands you can use with the client. To access the options of
each `command` you only need to do:

**Example**

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

Check how you can leverage the [directives](./directives/directives.md) of Lilya to power your
application.
