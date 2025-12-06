# WSGI Frameworks

Sabia que graças ao incrível trabalho do [a2wsgi](https://github.com/abersheeran/a2wsgi) pode integrar qualquer framework WSGI (Flask, Django...)?

Sim, é verdade, agora pode facilmente migrar para Lilya sem ter que reescrever as suas aplicações antigas, na realidade, pode
reutilizá-las diretamente dentro de Lilya, até mesmo um Lilya que esteja a correr dentro de outro Lilya, um *Lilyaception*.

## WSGIMiddleware

Utilizar este middleware é bastante simples, vamos usar o Flask como exemplo, já que é muito rápido iniciar um serviço Flask em comparação com outros gigantes como Django.

=== "Roteamento Simples"

```python
{!> ../../../docs_src/wsgi/simple_routing.py!}
```

=== "Roteamento *Nested*"

```python
{!> ../../../docs_src/wsgi/nested_routing.py!}
```

=== "Roteamento Complexo"

```python
{!> ../../../docs_src/wsgi/complex_routing.py!}
```

=== "Vários Flask"

```python
{!> ../../../docs_src/wsgi/multiple.py!}
```

=== "Lilya"

```python
{!> ../../../docs_src/wsgi/lilya.py!}
```

=== "ChildLilya"

```python
{!> ../../../docs_src/wsgi/childlilya.py!}
```

Já tem uma ideia, as integrações são infinitas!

## Verifique

Com todos os exemplos anteriores, já pode verificar que as integrações estão a funcionar.

Os caminhos que se referem ao `WSGIMiddleware` serão tratados pelo Flask e o resto será tratado pelo **Lilya**, incluindo Lilya dentro de outro Lilya.

Se executar o *endpoint* tratado pelo Flask:

* `/flask` - No roteamento simples.
* `/flask` - No roteamento aninhado.
* `/internal/flask` e `/external/second/flask` - No roteamento complexo.
* `/flask` e `/second/flask` - A partir de várias aplicações Flask.
* `/lilya/flask` e `/lilya/second/flask` - A partir de dentro de outro Lilya.

Verá a resposta:

```shell
Hello, Lilya from Flask!
```

Ao aceder a qualquer endpoint do `Lilya`:

* `/home/lilya` - No roteamento simples.
* `/home/lilya` - No roteamento complexo.
* `/home/lilya` - No roteamento aninhado.
* `/home/lilya` - A partir de várias aplicações Flask.
* `/lilya/home/lilya` - A partir de dentro de outro Lilya.

```json
{
    "name": "lilya"
}
```
