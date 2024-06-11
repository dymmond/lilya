# StaticFiles

Lilya fornece uma classe conveniente chamada `StaticFiles` para servir ficheiros de uma directoria especificada:

## Parâmetros

- `directory` - Uma string ou [os.PathLike][pathlike] indicando o caminho da directoria.
- `packages` - Uma lista de strings ou lista de tuplos de strings que representem modulos Python.
- `html` - Operar no modo HTML, carregando automaticamente o `index.html` para as directorias, se existir.
- `check_dir` - Garantir que a directoria exista ao instanciar. Por defeito é `True`.
- `follow_symlink` - Um booleano indicando se *symlinks* para ficheiros e diretorias devem ser seguidos. Por defeito é `False`.

```python
from lilya.apps import Lilya
from lilya.routing import Include
from lilya.staticfiles import StaticFiles


app = Lilya(routes=[
    Include('/static', app=StaticFiles(directory='static'), name="static"),
])
```

Para pedidos que não correspondem, os ficheiros estáticos responderão com respostas "404 Not Found" ou "405 Method Not Allowed".
No modo HTML, se existir um ficheiro `404.html`, será exibido como resposta 404.

A opção `packages` permite a inclusão de directorias "static" dentro de um módulo
O Python module "bootstrap4" segue como exemplo.

```python
from lilya.apps import Lilya
from lilya.routing import Include
from lilya.staticfiles import StaticFiles


app = Lilya(routes=[
    Include('/static', app=StaticFiles(directory='static', packages=['bootstrap4']), name="static"),
])
```

Por defeito, o `StaticFiles` procura pela directoria `statics` em cada módulo. Pode modificar o valor por defeito da directoria indicando
um tuplo de strings.

```python
routes=[
    Include('/static', app=StaticFiles(packages=[('bootstrap4', 'static')]), name="static"),
]
```

Embora possa optar por incluir ficheiros estáticos diretamente na directoria "static", usar *packaging* Python para incluir ficheiros
estáticos pode ser benéfico para agrupar componentes reutilizáveis.

[pathlike]: https://docs.python.org/3/library/os.html#os.PathLike
