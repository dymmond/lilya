---
hide:
  - navigation
---

# Lilya

<p align="center">
  <a href="https://lilya.dev"><img src="https://res.cloudinary.com/dymmond/image/upload/v1707501404/lilya/logo_quiotd.png" alt='Lilya'></a>
</p>

<p align="center">
  <em>🚀 Mais uma ferramenta ASGI que entrega. 🚀</em>
</p>

<p align="center">
<a href="https://github.com/dymmond/lilya/actions/workflows/test-suite.yml/badge.svg?event=push&branch=main" target="_blank">
    <img src="https://github.com/dymmond/lilya/actions/workflows/test-suite.yml/badge.svg?event=push&branch=main" alt="Test Suite">
</a>

<a href="https://pypi.org/project/lilya" target="_blank">
    <img src="https://img.shields.io/pypi/v/lilya?color=%2334D058&label=pypi%20package" alt="Package version">
</a>

<a href="https://pypi.org/project/lilya" target="_blank">
    <img src="https://img.shields.io/pypi/pyversions/lilya.svg?color=%2334D058" alt="Supported Python versions">
</a>
</p>

---

**Documentação**: [https://lilya.dev](https://lilya.dev) 📚

**Código font**: [https://github.com/dymmond/lilya](https://github.com/dymmond/lilya)

**A versão oficial suportada é sempre a mais recente lançada**.

---

## Motivação

No mundo do ASGI, ter alternativas é sempre ótimo e nenhuma ferramenta serve para tudo.
Lilya, vindo das grandes inspirações daqueles que abriram caminho, é uma ferramenta/framework Python mais simples, precisa, rápida e fácil de usar que visa a simplicidade.

Muitas vezes, não precisará de uma framework Python completa, pois pode ser avassalador para algumas tarefas simples. Em vez disso, poderá utilizar uma ferramenta ASGI simples que o ajude a desenhar aplicações prontas para produção, rápidas, elegantes, mantíveis e modulares.

É aqui que o Lilya se encaixa.

Com quase nenhuma dependência, 100% pythonico, totalmente tipado e pronto para produção.

## O que o Lilya traz?

Lilya vem com prendas incluídas.

* Uma toolkit/framework ASGI leve.
* Suporte para HTTP/WebSocket.
* Tarefas em segundo plano.
* Ciclo de vida de eventos (on_startup/on_shutdown e lifespan).
* Sistema de permissões nativo.
* Middlewares (Compressor, CSRF, Session, CORS...).
* Um cliente nativo e **opcional** [client](./lilya-cli.md).
* Sistema de controlo de gestão de diretivas para executar scripts personalizados dentro da aplicação.
* Poucas dependências.
* Compatibilidade com `trio` e `asyncio`.
* Sistema de roteamento dinâmico com a ajuda do **Include** nativo e mínima configuração.
* Sistema de configurações nativo.


## Instalação

Se deseja apenas o toolkit/framework.

```shell
$ pip install lilya
```

Se desejar utilizar funcionalidades extras como a **shell** ou **diretivas** (geração do esqueleto do projeto para acelerar o desenvolvimento inicial).

```shell
$ pip install lilya[cli,ipython] # para a shell ipython
$ pip install lilya[cli,ptpython] # para a shell ptpython
```

Pode aprender mais sobre o [cliente](./directives/discovery.md) na documentação.

Ou se quiser instalar tudo que permitirá usar todos os recursos do Lilya, como alguns middlewares específicos.

```shell
$ pip install lilya[all]
```

### Adicional

Também vai querer instalar um servidor local ASGI como o [uvicorn](https://www.uvicorn.org/) ou
[hypercorn](https://pgjones.gitlab.io/hypercorn/).

## Início rápido

Se está familiarizado com outras frameworks e toolkits Python, o Lilya proporciona a mesma sensação.

O Lilya também utiliza um [sistema de configurações nativo](./settings.md), o que pode ser extremamente útil para qualquer aplicação.

```python
{!> ../../../docs_src/quickstart/app.py !}
```

É muito simples. Embora haja muito a perceber aqui. Reparou no caminho `/{user}` que não apenas não requer que um `request` seja declarado, mas em vez disso, recebe um `user: str`?

Bem, o Lilya faz muita magia interna por si. Se não declarar um `request`, não há problema, ela só será passada se estiver presente.

Se tiver o parâmetro de caminho declarado na função também, o Lilya automaticamente procurará os parâmetros declarados e comparará com os parâmetros de caminho declarados no `Path` e os injetará por si.

Porreiro, não é? Isto é apenas a ponta do iceberg.

## Definições

O Lilya pode ser considerado uma framework ou uma ferramenta e a razão para isso é porque cada componente,
como middlewares, permissões, Path, Router... pode ser visto como uma aplicação ASGI independente.

Noutras palavras, pode construir um [middleware](./middleware.md) ou uma [permissão](./permissions.md) e
compartilhá-los com qualquer outra framework ASGI existente, o que significa que poderia criar uma
aplicação Lilya, middlewares, permissões e qualquer outro componente e reutilizá-los no [Esmerald][esmerald]
ou [FastAPI][fastapi] ou qualquer outro, na realidade.

**O Lilya não é uma framework completa como [Esmerald][esmerald] ou [FastAPI][fastapi], em vez disso,**
**é uma toolkit/framework leve que pode ser usada para construir essas frameworks, assim como trabalhar por conta própria.**

**Exemplo**


```python
{!> ../../../docs_src/quickstart/example.py !}
```

## Executar a aplicação

Para executar a aplicação do exemplo.

```shell
$ uvicorn myapp:app
INFO:     Started server process [140552]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

[esmerald]: https://lilya.dev/esmerald
[fastapi]: https://fastapi.tiangolo.com
