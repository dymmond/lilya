# The `@directive` decorator

Having [built-in directives](./directives.md) from Lilya is great as it gives you a lot of
niceties for your project but having **custom directives** is what really powers up your
application and takes it to another level.

But what if you want to use a modern client to declare directives?

Lilya uses [Sayer](https://sayer.dymmond.com) under the hood and now this allows to bring the
`@directive` decorator to make your life easier.

{!> ../../../docs_src/_shared/autodiscovery.md !}

!!! Tip
    As for Lilya 0.15.3+, both [custom directives](./custom-directives.md) and `@directive`
    are supported.

## The `@directive`

This is still a custom directive but using **Sayer** under the hood to run your directives.

On the contrary of [class based directives](./custom-directives.md), the syntax when using the `@directive`
is simpler when calling.

```python
lilya run <custom-directive> <ARGS>
```

Quite simple, right?

### Importing the decorator

This is even simpler:

```python
from lilya.cli.decorator import directive
```

### Where should directives be placed at?

All the custom directives created **must be** inside a `directives/operations` package in order to
be discovered.

The place for the `directives/operations` can be anywhere in your application and
you can have **more than one** as well.

Example:

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

As you can see from the previous example, we have four directives:

* **createsuperuser** - Inside `accounts/directives/operations`.
* **run_payroll** - Inside `payroll/directives/operations`.
* **createproduct** - Inside `products/directives/operations`.
* **db_shell** - Inside `./directives/operations`.

All of them, no matter where you put the directive, are inside a **directives/operations** where
lilya always looks at.

**This is the same as usual in Lilya, nothing has changed**.

## Help

There are two helps in place for the directives. The one you run the lilya executor (run) and the
one for the `directive`.

### --help

This command **is only used for the executor help**, for example:

```shell
$ lilya run --help
```

### -h/--h

This flag is used to access the `directive` help and not the `run`.

```shell
$ lilya run mydirective -h
```

Or

```shell
$ lilya run mydirective --h
```

### Notes

The **only way to see the help of a directive** is via `-h`/`--h`.

If `--help` is used, it will only show the help of the `run` and not the `directive` itself.

## Order of priority

**This is very important to understand**.

What happens if we have two custom directives with the same
name?

Let us use the following structure as example:

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

This example is simulating a structure of a lilya project with
**two custom directives with the same name**.

The first directive is inside `./directives/operations/` and the second inside
`./apps/accounts/directives/operations`.

Lilya directives work on a **First Found First Executed** principle and that means if you have
two custom directives with the same name, lilya will
**execute the first found directive with that given name**.

In other words, if you want to execute the `createsuperuser` from the `accounts`, the first found
directive inside `./directives/operations/` **shall have a different name** or else it will execute
it instead of the intended from `accounts`.

## Execution

Lilya directives use the same events as the one passed in the application.

For example, if you want to execute database operations and the database connections should be
established before hand, you can do in two ways:

* Use [Lifespan](../lifespan.md) events and the directives will use them.
* Establish the connections (open and close) inside the Directive directly.

The [pratical example](#a-practical-example) uses the [lifespan events](../lifespan.md) to
execute the operations. This way you only need one place to manage the needed application events.

## Example

Lets transform the example from [createsuperuser](./custom-directives.md#the-createsuperuser) into a `@directive` form.

As you could see from the explanation, its the same as the normal [class based directives](./custom-directives.md).

### The `createsuperuser` custom directive

Let's do the `createsuperuser` now using the `@directive`.

```python title="myproject/directives/operations/createsuperuser.py"
{!> ../../../docs_src/directives/example/createsuperuser_decorator.py !}
```

And this should be it. We now have a `createsuperuser` and an application and now we can run
in the command line:

**Using the --app or LILYA_DEFAULT_APP**

```shell
$ lilya --app myproject.main:app run createsuperuser --first-name Lilya --last-name Framework --email example@lilya.dev --username lilya --password lilya
```

Or

```shell
$ export LILYA_DEFAULT_APP=myproject.main:app
$ lilya run createsuperuser --first-name Lilya --last-name Framework --email example@lilya.dev --username lilya --password lilya
```

As you can see, the `@directive` acts as the class based directives but in a different syntax.
