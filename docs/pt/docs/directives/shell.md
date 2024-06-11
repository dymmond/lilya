# Suporte de Shell

Este é um suporte simples para uma shell interativa com o Lilya. Esta directiva simplesmente carrega algumas das configurações padrão, como `Path`, `Router`, `Include`, `WebSocketPth`, `settings` e economiza tempo sempre que precisa usar uma shell interativa para testar alguns processos ad-hoc.

O Lilya oferece essa possibilidade pronta para usar com a aplicação.

## Importante

Antes de ler esta secção, deve familiarizar-se com as formas como o Lilya lida com a descoberta das aplicações.

Os seguintes exemplos e explicações irão utilizar a abordagem [--app e variáveis de ambiente](./discovery.md#environment-variables), mas a [descoberta automática](./discovery.md#auto-discovery) é igualmente válida e funciona da mesma forma.

## Como funciona

O ecossistema do Lilya é complexo internamente, mas mais simples para o utilizador. O Lilya usará a descoberta da aplicação para entender algumas das suas configurações padrão e eventos e iniciar a shell.

### Requisitos

Para executar qualquer um das shells disponíveis, precisará ter o `ipython` ou `ptpython` ou ambos instalados.

**IPython**

```shell
$ pip install ipython
```

**PTPython**

```shell
$ pip install ptpython
```

### Como chamá-lo

#### Com [descoberta automática](./discovery.md#auto-discovery)

**Shell padrão**

```shell
$ lilya shell
```

**Shell PTPython**

```shell
$ lilya shell --kernel ptpython
```

#### Com [--app e variáveis de ambiente](./discovery.md#environment-variables)

**--app**

```shell
$ lilya --app myproject.main:app shell
```

**Variáveis de ambiente**

```shell
$ export LILYA_DEFAULT_APP=--app myproject.main:app
$ lilya shell --kernel ptpython
```

#### Se quiser usar as suas Configurações personalizadas

Às vezes, pode desejar usar as configurações da sua aplicação ao carregar a shell. Pode ver [mais detalhes](../settings.md) sobre as configurações e [como usá-las](../settings.md).

```shell
$ export LILYA_SETTINGS_MODULE=MyCustomSettings
$ export LILYA_DEFAULT_APP=--app myproject.main:app
$ lilya shell # padrão
$ lilya shell --kernel ptpython # iniciar com ptpython
```

### Como fica

O Lilya não carrega todas as variáveis globais e locais do Python por si. Em vez disso, carrega automaticamente os essenciais e algumas bibliotecas Python,
mas também pode importar outras ainda.

Fica assim:

<img src="https://res.cloudinary.com/dymmond/image/upload/v1707906253/lilya/wlhsrvtrpvgdvvbl75fc.png" alt='Exemplo de Shell'>

É claro que o `LILYA-VERSION` é substituído automaticamente pela versão que está a utilizar.

Bem porreiro, não é? Então é uma shell Python normal onde pode importar o que quiser e precisar, como numa interação normal com a shell Python.
