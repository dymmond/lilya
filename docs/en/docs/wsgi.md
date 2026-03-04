# WSGI frameworks

Did you know because of the awesome work from [a2wsgi](https://github.com/abersheeran/a2wsgi) you can integrate any wsgi
framework (Flask, Django...)?

Yes, that's right, you can now smoothly move to Lilya without rewriting your old applications from the scratch,
actually, you can reuse them directly within Lilya, even another Lilya running inside another Lilya,
a *Lilyaception*.

## WSGIMiddleware

Using this middleware is very simple, let's use Flask as example since it is very fast to spin-up a Flask service
compared to other giants like Django.

You can mount WSGI applications in multiple ways:

* directly in routes using `Include(..., app=WSGIMiddleware(...))`
* behind nested includes
* side-by-side with native Lilya routes

### Why this exists

This is mostly useful when:

* migrating incrementally from WSGI to ASGI;
* keeping legacy admin/billing modules while new APIs are built in Lilya;
* reusing existing Flask/Django WSGI apps under selected prefixes.

### Important behavior

* WSGI apps run in a sync model under the adapter.
* Lilya routes still run as native ASGI handlers.
* Prefix mapping decides which requests hit WSGI vs Lilya handlers.

!!! note
    Keep path boundaries explicit when mixing WSGI and Lilya. Prefix collisions are usually the main source of confusion.

=== "Simple Routing"

```python
{!> ../../../docs_src/wsgi/simple_routing.py!}
```

=== "Nested Routing"

```python
{!> ../../../docs_src/wsgi/nested_routing.py!}
```

=== "Complex Routing"

```python
{!> ../../../docs_src/wsgi/complex_routing.py!}
```

=== "Multiple Flask"

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

You already get the idea, the integrations are endless!

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

## Production notes

* Prefer clear mount prefixes (`/legacy`, `/admin`, etc.) over overlapping paths.
* Keep heavy async workloads in native ASGI routes when possible.
* Add request logging to verify traffic distribution between WSGI and Lilya branches.
