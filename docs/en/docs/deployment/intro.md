# Introduction

Deploying an **Lilya** application is relatively easy.

## What is a deployment

Deploying an application means to perform the necessary steps to make **your application available to others** to use
outside of your local machine and/or development environment.

Normally, deploying web APIs involves putting your code in remote machines with all the necessary requirements
from memeory, CPU, storage to things like networking and all of that. It will depend on your needs.

## Strategies

There are many ways of deploying an application. Every case is unique and it will depends on a lot of factors that
sometimes is not even related with the application itself. For example, **funds**.

You could want to save money not **going to cloud** but that also means more personal maintenance of the infrastructure.

You could also decide to go **cloud** and use an external provider such as **AWS**, **Azure**, **GCP** or even one that
is very good and also affordable like **render.com** or **Heroku**. It is your choice really since it will depend on
your needs.

The goal is not to tall you what to do but to give you a simple example in the case you would like to use, for example,
[docker](./docker.md) and the reason why it is very simple. **Every case is unique**.

## Lilya

We decided that we did not want to interfere with the way the people do deployments neither suggest that there is only
one way of doing it but we thought that would be very useful to have at least one example just to help out a bit and
to unblock some potential ideas.

We opted for using a standard, [docker](./docker.md).

## Deploying using Pydantic

Pydantic is fantastic handling with majority of the heavy lifting when it comes to read environment variables and
assigning but there are some tricks to have in mind.

### Loading List, dicts and complex types

When loading those into your environment variables **it is imperative** that you understand that Pydantic reads them
as a JSON like object.

**Example**:

```shell
export ALLOWED_HOSTS="https://www.example.com,https://www.foobar.com"
```

There are many ways of doing this but in the documentation of Pydantic (even a fix), they recommend to use the
`parse_env` and handle the parsing there.

```python
from typing import ClassVar

from dataclasses import dataclass, field

from lilya.conf import Settings


@dataclass
class AppSettings(Settings):
    allowed_hosts: list[str] | str = field(default=os.environ.get("ALLOWED_HOSTS", []))

    def __post_init__(self) -> None:
        self.allowed_hosts = self.allowed_hosts.split(",")

```
