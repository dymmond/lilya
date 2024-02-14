# WSGI frameworks

Did you know because of the awesome work from [a2wsgi](https://github.com/abersheeran/a2wsgi) you can integrate any wsgi
framework (Flask, Django...)?

Yes, that's right, you can now smoothly move to Lilya without rewriting your old applications from the scratch,
actually, you can reuse them directly within Lilya, even another Lilya running inside another Lilya,
a *Lilyaception*.

## WSGIMiddleware

Using this middleware is very simple, let's use Flask as example since it is very fast to spin-up a Flask service
compared to other giants like Django.

=== "Simple Routing"

    ```python
    {!> ../docs_src/wsgi/simple_routing.py!}
    ```

=== "Nested Routing"

    ```python
    {!> ../docs_src/wsgi/nested_routing.py!}
    ```

=== "Complex Routing"

    ```python
    {!> ../docs_src/wsgi/complex_routing.py!}
    ```

=== "Multiple Flask"

    ```python
    {!> ../docs_src/wsgi/multiple.py!}
    ```

=== "Lilya"

    ```python
    {!> ../docs_src/wsgi/lilya.py!}
    ```

=== "ChildLilya"

    ```python
    {!> ../docs_src/wsgi/childlilya.py!}
    ```

You already get the idea, the integrations are endeless!

## Check it

With all of examples from before, you can now verify that the integrations are working.

The paths pointing to the `WSGIMiddleware` will be handled by Flask and the rest is handled by **Lilya**,
including the Lilya inside another Lilya.

If you run the endpoint handled by Flask:

* `/flask` - From simple routing.
* `/flask` - From nested routing.
* `/internal/flask` and `/external/second/flask` - From complex routing.
* `/flask` and `/second/flask` - From multiple flask apps.
* `/lilya/flask` and `/lilya/second/flask` - From inside another Lilya

You will see the response:

```shell
Hello, Lilya from Flask!
```

Accessing any `Lilya` endpoint:

* `/home/lilya` - From simple routing.
* `/home/lilya` - From complex routing.
* `/home/lilya` - From nested routing.
* `/home/lilya` - From multiple flask apps.
* `/lilya/home/lilya` - From inside another Lilya

```json
{
    "name": "lilya"
}
```
