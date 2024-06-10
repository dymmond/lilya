# Environments

In a lot of projects, if not all of them, the environment variables are used for deployments
or to simply not to expose the secrets in the codebase.

There are many libraries you can use to make your life esier like `load_env`, for example.

Although these libraries are powerful, they might lack in simplicity of use and to help you with
that, Lilya is shipped with a `EnvironLoader` functionality.

```python
from lilya.environments import EnvironLoader
```

## The `EnvironLoader`

This object is simply a wrapper on top of the already used [multidict](https://multidict.aio-libs.org/en/stable/)
which does a lot of magic for us.

The purpose of the `EnvironLoader` is to make the process of loading and parsing simpler and direct
for you without extra complications.

## How to use it

The configurations of the application should be stored inside environment variables, for example,
inside an `.env` file.

A good example of this practice is the access to a specific database, you don't want to hard code
the credentials directly!

**The `EnvironLoader` reads from the `.env` as well as from the system environments. See the [order of priority](#order-of-priority) for more details.**

There are two ways of using the `EnvironLoader`.

* Via [`env()`](#via-env).
* Via [direct access](#via-direct-access).

Let us assume we have an `.env` file containing the following values and store them in a [settings](./settings.md)
object specific from Lilya.

```shell title=".env"
DATABASE_NAME=mydb
DATABASE_USER=postgres
DATABASE_PASSWD=postgres
DATABASE_HOST=a-host-somewhere.com
DATABASE_PORT=5432
API_KEY=XXXXX
```

Let us see how we can use both approaches to extract the values.

### Via `env()`

For those familiar with external libraries, this way follows the same principle. Very easy to understand and use.

```python
{!> ../../../docs_src/environments/normal.py!}
```

### Via direct access

With direct access is pretty much the same but without calling the `env()` function.

```python
{!> ../../../docs_src/environments/normal.py!}
```

## Order of priority

There is an order of priority in how the [EnvironLoader](#the-environloader) operates and reads the values:

* From an environment variable.
* From an `.env` file declared.
* From the default value given in `loader`.

## Parameters

* **env_file** - A string path of the location `.env`.
* **environ** - Optional dictionary containing specific environment variables. It defaults to
`os.environ` if nothing is provided.
* **prefix** - A string `prefix` to be concatenated to all the loaded environment variables.
* **ignore_case** - Boolean flag indicating if an environment variable can be in lowercase. Defaults
to false and internally transforms all the lowercase variables into uppercase().
