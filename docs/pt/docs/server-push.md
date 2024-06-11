# Push do Servidor

Lilya incorpora o suporte para push do servidor em `HTTP/2` e `HTTP/3`,
permitindo a entrega proativa de recursos ao cliente para acelerar o tempo de carregamento da página.

## O método

Este método é usado para iniciar um push do servidor para um recurso.
Se a funcionalidade de push do servidor não estiver disponível, este método não faz nada.

- `path`: Uma string especificando o caminho do recurso.

```python
{!> ../../../docs_src/push/server.py !}
```
