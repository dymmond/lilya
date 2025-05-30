# Application Discovery

Lilya has many different ways of understanding the commands, one is via
[environment variables](#environment-variables) and another is via [auto discovery](#auto-discovery).

## Auto Discovery

If you are familiar with other frameworks like Django, you are surely familiar with the way the
use the `manage.py` to basically run every command internally.

Lilya doesn't have a `manage.py` and it is not opinionated on that level like that since it
is not a monolith (unless **you design to be**).

Although not having that same level, Lilya does a similar job by having "a guess" of what
it should be and throws an error if not found or if no [environment variables or --app](#environment-variables)
are provided.

**The application discovery works as an alternative to providing the `--app` or a `LILYA_DEFAULT_APP` environment variable**.

So, what does this mean?

This means if **you do not provide an --app or a LILYA_DEFAULT_APP**, Lilya will try to find the
lilya application for you automatically.

Let us see a practical example of what does this mean.

Imagine the following folder and file structure:

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

The structure above of `myproject` has a lot of files and the one higlighted is the one that
contains the `Lilya` application object.

### How does it work?

When no `--app` or no `LILYA_DEFAULT_APP` environment variable is provided, Lilya will
**automatically look for**:

* The current directory where the directive is being called contains a file called:
    * **main.py**
    * **app.py**
    * **application.py**

    !!! Warning
        **If none of these files are found**, Lilya will look **at the first children nodes, only**,
        and repeats the same process. If no files are found then throws an `EnvError`
        exception.

* Once one of those files is found, Lilya will analise the type of objects contained in the
module and will check if any of them is a valid `Lilya` type and return it.

* If Lilya understand that none of those objects are type `Lilya` (or subclasses), it will
do one last attempt and try to find specific function declarations:
    * **get_application()**
    * **get_app()**

This is the way that Lilya can `auto discover` your application.

!!! Note
    Flask has a similar pattern for the functions called `create_app`. Lilya doesn't use the
    `create_app`, instead uses the `get_application` or `get_app` as a pattern as it seems cleaner.

## Environment variables

When using some of the custom directives or built-in directives with this method, Lilya
**expects at least one environment variable to be present**.

* **LILYA_DEFAULT_APP** - The Lilya application to run the directives against.

The reason for this is because every Lilya application might differ in structure and design.
Lilya not being opinionated in the way you should assemble, the application needs to know
**at least where the entry-point is going be**.

Also, gives a clean design for the time when it is needed to go to production as the procedure is
very likely to be done using environment variables.

So to save time you can simply do:

```shell
$ export LILYA_DEFAULT_APP=myproject.main:app
```

Or whatever location you have.

Alternatively, you can simply pass `--app` as a parameter with the location of your application
instead.

Example:

```shell
$ lilya --app myproject.main:app show-urls
```

## How to use and when to use it

Previously it was used a folder structure as example and then an explanation of how Lilya would
understand the auto discovery but in practice, how would that work?

Let us use some of the core Lilya internal directives and run them against that same structure.

**This is applied to any [directive](./directives.md) or [custom directive](./custom-directives.md)**.

Let us see again the structure, in case you have forgotten already.

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

The `main.py` is the file that contains the `Lilya` application. A file that could look like
this:

```python title="myproject/src/main.py"
{!> ../../../docs_src/directives/discover.py !}
```

This is a simple example with two endpoints, you can do as you desire with the patterns you wish to
add and with any desired structure.

What will be doing now is run the following directives using the [auto discovery](#auto-discovery)
and the [--app or LILYA_DEFAULT_APP](#environment-variables):

* **directives** - Lists all the available directives of the project.
* **runserver** - Starts the development server.

We will be also executing the directives inside `myproject`.

**You can see more information about these [directives](./directives.md), including**
**parameters, in the next section.**

### Using the auto discover

#### directives

##### Using the auto discover

```shell
$ lilya directives
```

Yes! Simply this and because the `--app` or a `LILYA_DEFAULT_APP` was provided, it triggered the
auto discovery of the Lilya application.

Because the application is inside `src/main.py` it will be automatically discovered by Lilya as
it followed the [discovery pattern](#how-does-it-work).

##### Using the --app or LILYA_DEFAULT_APP

This is the other way to tell Lilya where to find your application. Since the application is
inside the `src/main.py` we need to provide the proper location is a `<module>:<app>` format.

###### --app

With the `--app` flag.

```shell
$ lilya --app src.main:app directives
```

###### LILYA_DEFAULT_APP

With the `LILYA_DEFAULT_APP`.

Export the env var first:

```shell
$ export LILYA_DEFAULT_APP=src.main:app
```

And then run:

```shell
$ lilya directives
```

#### runserver

Now this is a beauty! This directive is special and **should be only used for development**. You
can see [more details](./directives.md#runserver) how to use it and the corresponding parameters.

It is time to run this directive.

!!! Note
    For development purposes, Lilya uses `uvicorn`. If you don't have it installed, please run
    `pip install uvicorn`.

##### Using the auto discover

```shell
$ lilya runserver
```

Again, same principle as before because the `--app` or a `LILYA_DEFAULT_APP` was provided,
it triggered the auto discovery of the Lilya application.

##### Using the --app or LILYA_DEFAULT_APP

###### --app

With the `--app` flag.

```shell
$ lilya --app src.main:app runserver
```

###### LILYA_DEFAULT_APP

With the `LILYA_DEFAULT_APP`.

Export the env var first:

```shell
$ export LILYA_DEFAULT_APP=src.main:app
```

And then run:

```shell
$ lilya runserver
```
