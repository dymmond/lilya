# Shell Support

This is a simple support for an interactive shell with Lilya. This directive simply loads some
of the defaults such as `Path`, `Router`, `Include`, `WebSocketPth`, `settings` and saving you
time every time you need to use an interactive shell to test some ad-hoc processes.

Lilya gives you that possibility completely out of the box and ready to use with your
application.

## Important

Before reading this section, you should get familiar with the ways Lilya handles the discovery
of the applications.

The following examples and explanations will be using the [auto discovery](./discovery.md#auto-discovery)
but [--app and environment variables](./discovery.md##environment-variables) approach but the
is equally valid and works in the same way.

## How does it work

Lilya ecosystem is complex internally but simpler to the user. Lilya will use the application
discovery to understand some of your defaults and events and start the shell.

### Requirements

To run any of the available shells you will need `ipython` or `ptpython` or both installed.

**IPython**

```shell
$ pip install ipython
```

or

```shell
$ pip install lilya[ipython]
```

**PTPython**

```shell
$ pip install ptpython
```

or

```shell
$ pip install lilya[ptpyton]
```

### How to call it

#### With [auto discovery](./discovery.md#auto-discovery)

**Default shell**

```shell
$ lilya shell
```

**PTPython shell**

```shell
$ lilya shell --kernel ptpython
```

#### With [--app and environment variables](./discovery.md##environment-variables)

**--app**

```shell
$ lilya --app myproject.main:app shell
```

**Environment variables**

```shell
$ export LILYA_DEFAULT_APP=--app myproject.main:app
$ lilya shell --kernel ptpython
```

#### If you want to use your custom Settings

Sometimes you want to use your application settings as well while loading the shell. You can see
[more details](../settings.md) about the settings and [how to use them](../settings.md).

```shell
$ export LILYA_SETTINGS_MODULE=MyCustomSettings
$ export LILYA_DEFAULT_APP=--app myproject.main:app
$ lilya shell # default
$ lilya shell --kernel ptpython # start with ptpython
```

### How does it look like

Lilya doesn't want to load all python globals and locals for you. Instead loads all the
essentials and some python packages automatically for you but you can still import others.

It looks like this:

<img src="https://res.cloudinary.com/dymmond/image/upload/v1707906253/lilya/wlhsrvtrpvgdvvbl75fc.png" alt='Shell Example'>

Of course the `LILYA-VERSION` is replaced automatically by the version you are using.

Pretty cool, right? Then it is a normal python shell where you can import whatever you want and
need as per normal python shell interaction.
