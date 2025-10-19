# Environments

Environment variables are essential for configuration, deployments, and keeping secrets out of your codebase.

Lilya provides a built-in, powerful yet simple utility called **`EnvironLoader`**, a unified environment manager that can load from:

* **System environment variables**
* **`.env` files**
* **YAML configuration files**
* **Overrides (in-memory dicts)**

with **variable expansion**, **prefixing**, **type casting**, and **read-only safety** built in.

```python
from lilya.environments import EnvironLoader
```

## The `EnvironLoader`

`EnvironLoader` extends [`multidict`](https://multidict.aio-libs.org/en/stable/) to provide a consistent interface for reading,
expanding, and managing configuration values across multiple sources.

It makes loading configuration **safe, deterministic, and easily testable**.

## Features

* ✅ **Load from multiple sources** (`.env`, YAML, OS environment, dict overrides)
* ✅ **Variable expansion** — supports `$VAR` and `${VAR|default}` syntax
* ✅ **Type casting** — convert values to `int`, `bool`, `float`, etc.
* ✅ **Boolean parsing** — recognizes `true`, `yes`, `1`, `on`, etc.
* ✅ **Flatten nested YAML** into dot-separated keys (`db.host`, `db.port`)
* ✅ **Prefix support** — auto-prepend prefixes to lookups
* ✅ **Case-insensitive mode** (e.g. `db_user` == `DB_USER`)
* ✅ **Override layers** for testing or runtime substitutions
* ✅ **Immutable once read** — prevents accidental mutation after use

## Basic Usage

Let's start with a simple `.env` file:

```shell title=".env"
DATABASE_NAME=mydb
DATABASE_USER=postgres
DATABASE_PASSWD=postgres
DATABASE_HOST=a-host-somewhere.com
DATABASE_PORT=5432
API_KEY=xxxxx
DEBUG=true
```

### Via `env()`

```python
{!> ../../../docs_src/environments/normal.py !}
```

### Via direct access

```python
loader = EnvironLoader(env_file=".env")

print(loader["DATABASE_NAME"])  # mydb
print(loader["API_KEY"])        # xxxxx
```

Both styles are valid, `env()` just gives you optional type casting and default handling.

## Type Casting and Boolean Handling

You can automatically cast values when using `env()`:

```python
loader.env("DATABASE_PORT", cast=int)     # 5432
loader.env("DEBUG", cast=bool)            # True
loader.env("TIMEOUT", cast=float, default=5.5)
```

Booleans accept the following case-insensitive values:

| Truthy                        | Falsy                          |
| :---------------------------- | :----------------------------- |
| `true`, `1`, `y`, `yes`, `on` | `false`, `0`, `n`, `no`, `off` |


## Variable Expansion

You can reference existing environment variables within `.env` or YAML files:

```shell title=".env"
APP_NAME=myapp
LOG_PATH=/var/log/${APP_NAME|default_app}
```

Supports:

* `$VAR`
* `${VAR}`
* `${VAR|default}`

Example:

```python
loader = EnvironLoader(env_file=".env")
print(loader["LOG_PATH"])  # /var/log/myapp
```

If a variable is missing and no default is given, Lilya raises `EnvError` in **strict mode**.

## YAML Support

You can load from YAML as well:

```yaml title="config.yaml"
database:
  host: localhost
  ports: [5432, 5433]
service:
  name: ${APP_NAME|myservice}
```

### Example

```python
loader = EnvironLoader()
loader.load_from_files(yaml_file="config.yaml")

print(loader["database.host"])      # localhost
print(loader["database.ports.0"])   # 5432
print(loader["service.name"])       # myservice
```

By default, YAML data is **flattened** to dot-separated keys.
To keep nested structures intact:

```python
loader.load_from_files(yaml_file="config.yaml", flatten=False)
```

## Order of Precedence

When loading from multiple sources, the order of priority (lowest → highest) is:

1. Initial values passed to `EnvironLoader(...)`
2. OS environment (`os.environ`)
3. `.env` file
4. YAML file
5. `overrides` dictionary

That means later layers override earlier ones automatically.


## Overriding at Runtime

You can override or inject variables dynamically (useful for tests):

```python
loader = EnvironLoader(env_file=".env")
loader.load_from_files(overrides={"DEBUG": False, "CACHE_BACKEND": "memory"})
```

Overrides always take the highest precedence.


## Prefixes

You can apply a prefix to all lookups:

```python
loader = EnvironLoader(env_file=".env", prefix="APP_")
print(loader.env("DATABASE_USER"))  # resolves APP_DATABASE_USER
```

Useful when sharing the same `.env` for multiple apps.

## Case Insensitivity

To ignore case in variable names:

```python
loader = EnvironLoader(env_file=".env", ignore_case=True)
```

Then both `db_user` and `DB_USER` resolve to the same key.

## Immutable Read Behavior

Once you read a variable via `env()` or `loader["KEY"]`, that key becomes **read-only**.

Any attempt to change or delete it afterwards raises `EnvError`.

Example:

```python
loader.env("DATABASE_USER")  # Marked as read
loader["DATABASE_USER"] = "root"  # ❌ Raises EnvError
```

This ensures your configuration stays consistent once accessed.

## Utility Methods

| Method                               | Description                                                    |
| :----------------------------------- | :------------------------------------------------------------- |
| `env(key, cast=None, default=Empty)` | Retrieves a value, optionally cast to a type.                  |
| `__getitem__(key)`                   | Dictionary-style lookup, marks key as read-only.               |
| `__setitem__(key, value)`            | Sets a variable (unless it's already read).                    |
| `load_from_files(...)`               | Load from `.env`, YAML, and overrides.                         |
| `export()`                           | Return all current values as a plain `dict`.                   |
| `multi_items()`                      | Generator yielding all key/value pairs (including duplicates). |
| `get_multi_items()`                  | Returns a list of all multi-item pairs.                        |

## Example: Combined Configuration

```python
loader = EnvironLoader(
    env_file=".env",
    yaml_file="config.yaml",
    ignore_case=True,
    prefix="APP_",
)

loader.load_from_files(
    include_os_env=True,
    overrides={"DEBUG": False},
)

print(loader.export())
```

This will:

1. Start from OS environment.
2. Layer `.env` and YAML.
3. Apply case insensitivity and `APP_` prefix.
4. Apply runtime overrides (`DEBUG=False`).
5. Return a complete merged dictionary of configuration.

## Errors and Strict Mode

If you enable strict mode (default):

* Duplicate keys in `.env` → `EnvError`
* Missing variable expansion → `EnvError`

To relax it:

```python
loader.load_from_files(env_file=".env", strict=False)
```

Warnings will be issued instead of errors.

## Summary

| Capability                         |  Supported |   |
| :--------------------------------- | :--------: | - |
| `.env` loading                     |      ✅     |   |
| YAML loading                       |      ✅     |   |
| Variable expansion (`$VAR`, `${VAR | default}`) | ✅ |
| Boolean parsing                    |      ✅     |   |
| Type casting                       |      ✅     |   |
| Prefix support                     |      ✅     |   |
| Case insensitivity                 |      ✅     |   |
| Overrides                          |      ✅     |   |
| Flatten nested YAML                |      ✅     |   |
| Immutable reads                    |      ✅     |   |

Lilya's `EnvironLoader` gives you a single, elegant API for managing configuration safely across environments and deployment targets.
