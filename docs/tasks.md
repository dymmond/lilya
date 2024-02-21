# Tasks

This can be useful for those operations that need to happen after the request without blocking the
client (the client doesn't have to wait to complete) from receiving that same response.

To associate a background task with a response, the task will execute only after the response has been dispatched,
this means that a background task **must be attached** to a [Response](./responses.md).

Example:

* Registering a user in the system and send an email confirming the registration.
* Processing a file that can take "some time". Simply return a HTTP 202 and process the file in the
background.

### Using a list

Of course there is also the situation where more than one background task needs to happen.

```python
{!> ../docs_src/background_tasks/via_list.py !}
```

## Via response

Adding tasks via response will be probably the way you will be using more often and the reson being
is that sometimes you will need some specific information that is only available inside your view.

### Using a single instance

In the same way you created a single background task for the handlers, in the response works in a
similar way.

### Using a list

The same happens when executing more than one background task and when more than one operation is
needed.

```python
{!> ../docs_src/background_tasks/response/via_list.py !}
```

### Using the add_task

Another way of adding multiple tasks is by using the `add_tasks` function provided by the
`Tasks` object.

```python
{!> ../docs_src/background_tasks/response/add_tasks.py !}
```

The `.add_task()` receives as arguments:

* A task function to be run in the background (send_email_notification and write_in_file).
* Any sequence of arguments that should be passed to the task function in order (email, message).
* Any keyword arguments that should be passed to the task function.


## Technical information

The class `Task` and `Tasks` come directly from `lilya.background` but the nature of the
objects also allows the use of external libraries like [backgrounder](https://backgrounder.dymmond.com).

You can use `def` or `async def` functions when declaring those functionalities to be passed to
the `Task` and Lilya will know how to handle those for you.

The `Tasks` obejct also accepts the `as_group` parameter. This enables `anyio` to create a task
group and run them.
