# Tasks

Isto pode ser útil para operações que precisam de acontecer após o pedido sem bloquear o
cliente (o cliente não precisa esperar que complete) para receber a resposta.

Para associar uma tarefa em segundo plano com uma resposta, a tarefa será executada somente após a resposta ter sido enviada,
isto significa que uma tarefa em segundo plano **deve ser anexada** a uma [Resposta](./responses.md).

Exemplo:

* Registrar um utilizador no sistema e enviar um e-mail a confirmar o registro.
* Processar um ficheiro que pode levar "algum tempo". Simplesmente retorna um HTTP 202 e processa o ficheiro em segundo plano.

### Usando uma lista

É claro que também há situações em que mais de uma tarefa em segundo plano pode acontecer.

```python
{!> ../../../docs_src/background_tasks/via_list.py !}
```

## Através da resposta

Adicionar tarefas através da resposta provavelmente será a maneira que usará com mais frequência e o motivo é
que às vezes precisará de algumas informações específicas que só estão disponíveis dentro da sua *view*.

### Usando uma única instância

Da mesma forma que criou uma única tarefa em segundo plano para os *handlers*, na resposta funciona de maneira
semelhante.

### Usando uma lista

O mesmo acontece ao executar mais do que uma tarefa em segundo plano e quando mais do que uma operação é
necessária.

```python
{!> ../../../docs_src/background_tasks/response/via_list.py !}
```

### Usando o add_task

Outra maneira de adicionar várias tarefas é utilizando a função `add_tasks` fornecida pelo
objecto `Tasks`.

```python
{!> ../../../docs_src/background_tasks/response/add_tasks.py !}
```

O `.add_task()` recebe como argumentos:

* Uma função de tarefa a ser executada em segundo plano (send_email_notification e write_in_file).
* Qualquer sequência de argumentos que devem ser passados para a função de tarefa na ordem (email, message).
* Quaisquer argumentos de palavra-chave que devem ser passados para a função de tarefa.


## Informações técnicas

As classes `Task` e `Tasks` derivam diretamente de `lilya.background`, mas a natureza dos
objectos também permite o uso de bibliotecas externas como [backgrounder](https://backgrounder.dymmond.com).

Pode usar funções `def` ou `async def` ao declarar essas funcionalidades para serem passadas para
o `Task` e o Lilya saberá como lidar com isso.

O objecto `Tasks` também aceita o parâmetro `as_group`. Isso permite que o `anyio` crie um grupo de tarefas
e as execute.
