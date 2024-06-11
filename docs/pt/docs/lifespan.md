# Lifespan

Estes são extremamente comuns para os casos em que precisa definir a lógica que deve ser executada no início da aplicação e no encerramento.

Antes de iniciar significa que o código (lógica) será executado **uma vez** antes de começar a receber pedidos e o mesmo ocorre no encerramento,
onde a lógica também é executada **uma vez** após ter gerido, muito provavelmente, muitos pedidos.

Isso pode ser particularmente útil para configurar os recursos da sua aplicação e limpa-los. Esses ciclos abrangem toda a aplicação.

## Tipos de eventos

Atualmente, o Lilya suporta **on_startup**, **on_shutdown** e **lifespan**.

### Lilya on_startup e on_shutdown

Se passar os parâmetros `on_startup` e `on_shutdown` em vez do `lifespan`, o Lilya
irá **gerar automaticamente o gestor de contexto assíncrono** por si e passá-lo para o `lifespan`
internamente.

**Pode utilizar on_startup/on_shutdown e lifespan, mas não ambos ao mesmo tempo**.

!!! tip
    O `shutdown` geralmente ocorre quando você para a aplicação.

### Funções

Para definir as funções a serem usadas nos eventos, pode definir uma função `def` ou `async def`.
O Lilya saberá o que fazer com elas e as gerirá por si.

## Como utilizar

Utilizar esses eventos é bastante simples e claro. Como mencionado anteriormente, existem duas maneiras:

1. Através do [on_startup e on_shutdown](#on_startup-e-on_shutdown)
2. Através do [lifespan](#lifespan)

Nada como um exemplo de utilização para entender melhor.

Vamos supor que queira adicionar uma base de dados à sua aplicação e, como isso pode ser caro,
também não quer fazer isso para cada pedido mas sim num nível da aplicacional, ao iniciar e encerrar.

Vamos ver como é ficaria usando os eventos disponíveis actualmente.

Vamos utilizar o [Saffier](https://saffier.tarsild.io) como exemplo.

### on_startup e on_shutdown

Utilizando o caso de uso da base de dados definida acima:

```python
{!> ../../../docs_src/events/start_shutdown.py !}
```
Como pode ver, quando a aplicação está a iniciar, declaramos a `database.connect()`,
assim como o `database.disconnect()` ao encerrar.

### Lifespan

O que acontece se usarmos o [exemplo acima](#on_startup-e-on_shutdown) e o convertermos para um evento do tipo lifespan?

Bem, este também é muito simples, mas a forma como é montado é ligeiramente diferente.

Para definir os eventos de *início* e *encerramento*, precisa de um *gestor de contexto* para que isso aconteça.

Vamos ver o que isso significa em exemplos práticos, alterando o exemplo anterior para um `lifespan`.

```python
{!> ../../../docs_src/events/lifespan.py !}
```

Isto é algo bastante complexo de compreender. O que está realmente a acontecer?

Portanto, antes era necessário declarar explicitamente os eventos `on_startup` e `on_shutdown` nos parâmetros correspondentes na aplicação Lilya,
mas com o `lifespan` isso é feito **apenas num lugar**.

A primeira parte antes do `yield` será executada **antes da aplicação iniciar** e a segunda parte após o `yield` será executada **após a aplicação terminar**.

A função `lifespan` recebe um parâmetro `app: Lilya` porque é injetada na aplicação e a framework saberá o que fazer com ela.

### Gestor de contexto assíncrono

Como pode verificar, a função [lifespan](#lifespan) está decorada com `@asynccontextmanager`.

Isto é *standard* em Python para utilizar um `decorator` e este, em particular, converte a função `lifespan` em algo chamado **gestor de contexto assíncrono**.

```python
{!> ../../../docs_src/events/lifespan.py !}
```

Em Python, um **gestor de contexto** é algo que pode usar com a palavra-chave `with`. Um amplamente utilizado, por exemplo, é com o `open()`.

```python
with open("file.txt", 'rb') file:
    file.read()
```

Quando um gestor de contexto ou gestor de contexto assíncrono é criado como o exemplo acima,
o que acontece é que antes de entrar no `with`, ele executará o código **antes** do `yield` e ao sair do bloco de código,
ele executará o código **depois** do `yield`.

O parâmetro lifespan do Lilya aceita um **gestor de contexto assíncrono**,
o que significa que podemos adicionar nosso novo gestor de contexto assíncrono `lifespan` diretamente.

## Curiosidade sobre gestores de contexto assíncronos

Esta secção está fora do âmbito do ciclo de vida e eventos do Lilya e é **apenas por curiosidade**.
Por favor, consulte a secção [ciclo de vida](#lifespan) pois, no caso do Lilya, a forma de **declar é diferente**
e um parâmetro `app: Lilya` é **sempre necessário**.

### General approach to async context managers

Em geral, ao usar um contexto assíncrono, o princípio é o mesmo que um gestor de contexto normal, com a diferença
principal de que usamos `async` antes do `with`.

Vamos ver um exemplo ainda usando o ORM [Saffier](https://saffier.tarsild.io).

!!! Warning
    Novamente, isso é para fins gerais, não para o uso do ciclo de vida do Lilya.
    O exemplo de como usá-lo é descrito na seção [lifespan](#lifespan).

#### Utilizando funções

```python
{!> ../../../docs_src/events/curiosities/example.py !}
```

Como pode ver, utilizamos o `@asynccontextmanager` para transformar nossa função num gestor de contexto `async` e o `yield`
é o responsável por gerir o comportamento de entrada e saída.

#### Utilizando classes em Python

E se construíssemos um gerenciador de contexto assíncrono com classes em Python?
Bem, isso é ainda melhor, pois pode "visualmente" ver e perceber o comportamento.

Vamos voltar ao mesmo exemplo com o ORM [Saffier](https://saffier.tarsild.io).

```python
{!> ../../../docs_src/events/curiosities/classes.py !}
```

Este exemplo é bastante claro. O `aenter` é equivalente ao que acontece antes do `yield` no nosso exemplo anterior
e o `aexit` é o que acontece após o `yield`.

Desta vez, não foi necessário decorar a classe com `@asynccontextmanager`.
O comportamento implementado é feito através de `aenter` e `aexit`.

Os gestores de contexto assíncronos podem ser uma ferramenta poderosa na sua aplicação.
