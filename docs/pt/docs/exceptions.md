# Excepções & Exception Handlers

*Exception handlers* são, como o nome sugere, as funções que lidam com excepções do tipo X caso ocorram.

## Exception handlers

Em cada nível o parâmetro `exception_handler` (entre outros) está disponível para ser utilizado e pronto a lidar com
excepções espeíficas para cada nível.

As *exception handlers* são declaras num dicionário python e pode passar como chave a excepção em si ou o `status_code`
que vai sempre utilizar a excepção em si.

```python
{!> ../../../docs_src/exception_handlers/precedent.py !}
```

### O que está a acontecer

O nível da aplicação contém um manipulador de excepções `handle_type_error` e handle_value_error e isso significa que para
toda `HTTPException` e `ValueError` lançada na aplicação, será tratada por essa função.

### Exception handlers personalisadas

Todos sabemos que Lilya lida muito bem com excepções por design, mas às vezes também podemos
querer lançar um erro ao fazer alguma lógica de código que não está diretamente relacionada com um `data` de
um *exception handler*.

**Examplo**

```python
{!> ../../../docs_src/exception_handlers/example.py !}
```

Este exemplo não é nada comum, mas serve para mostrar onde uma excepção é lançada.

Lilya oferece **um** *exception handler* personalizado **pronto a usar**:

* **handle_value_error** - Quando se quer que a excepção `ValueError` seja automaticamente convertida
num JSON.

```python
from lilya._internal._exception_handlers import handle_value_error
```

Como ficaria o exemplo anterior utilizando este *exception handler* personalizado?

```python
{!> ../../../docs_src/exception_handlers/example_use.py !}
```

## Uso dos status codes

Ao declarar *exception handlers*, como mencionado anteriormente, pode-se usar *status codes* em vez da
própria excepção. Isto permite e indica como uma excepção deve ser tratada quando ocorre um `status_code`
específico.

Isto pode ser muito útil se apenas se quiser restringir à abordagem do `status_code` em vez da
própria `Exception`.

```python
{!> ../../../docs_src/exception_handlers/status_codes.py !}
```

## HTTPException

A classe `HTTPException` serve como uma classe fundamental adequada para lidar com várias excepções.
Na implementação padrão do `ExceptionMiddleware`, respostas HTTP no formato de texto simples são retornadas em qualquer instância de `HTTPException`.

!!! Note
    O uso correto dita que se deve lançar o `HTTPException` exclusivamente dentro de rotas ou endpoints.
    Middleware e Permissões, por outro lado, devem simplesmente retornar as respostas apropriadas diretamente.

## WebSocketException

A classe `WebSocketException` é desenhada para lançar erros especificamente dentro de endpoints WebSocket.
