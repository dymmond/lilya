# Ambientes

Em muitos projetos, se não todos, as variáveis de ambiente são utilizadas para *deployments* ou para simplemente não
expor qualquer informação secreta do código-fonte.

Existem muitas bibliotecas que pode utilizar para facilitar sua vida, como `load_env`, por exemplo.

Embora essas bibliotecas sejam poderosas, elas podem ser carentes em simplicidade de utilização.
Para ajudá-lo com isso, o Lilya fornece a funcionalidade `EnvironLoader`.

```python
from lilya.environments import EnvironLoader
```

## O `EnvironLoader`
# Ambientes

Neste caso, este objeto é apenas um invólucro em cima do [multidict](https://multidict.aio-libs.org/en/stable/), que faz muita magia por nós.

O objetivo do `EnvironLoader` é tornar o processo de carregamento e análise mais simples e direto, sem complicações extras.

## Como utilizar

As configurações da aplicação devem ser armazenadas em variáveis de ambiente, por exemplo, dentro de um ficheiro `.env`.

Um bom exemplo dessa prática é o acesso a uma base de dados específica onde não quer codificar as credenciais diretamente!

**O `EnvironLoader` lê tanto do ficheiro `.env` quanto das variáveis de ambiente do sistema. Consulte a [ordem de prioridade](#order-of-priority) para mais detalhes.**

Existem duas formas de utilizar o `EnvironLoader`.

* Através do [`env()`](#via-env).
* Através do acesso direto.

Vamos supor que temos um ficheiro `.env` que contém os seguintes valores e onde estão declarados num [settings](./settings.md) específico do Lilya.

```shell title=".env"
DATABASE_NAME=mydb
DATABASE_USER=postgres
DATABASE_PASSWD=postgres
DATABASE_HOST=a-host-somewhere.com
DATABASE_PORT=5432
API_KEY=XXXXX
```

Vamos ver como podemos usar ambas as abordagens para extrair os valores.

### Via `env()`

Para aqueles familiarizados com bibliotecas externas, este método segue o mesmo princípio. Muito fácil de perceber e usar.

```python
{!> ../../../docs_src/environments/normal.py!}
```

### Via Acesso direto

Com o acesso direto é praticamente a mesma coisa, mas sem chamar a função `env()`.

```python
{!> ../../../docs_src/environments/normal.py!}
```
## Ordem de prioridade

Existe uma ordem de prioridade na forma como o [EnvironLoader](#o-environloader) opera e lê os valores:

* A partir de uma variável de ambiente.
* A partir de um ficheiro `.env` declarado.
* A partir do valor padrão fornecido no `loader`.

## Parâmetros

* **env_file** - Uma string com o caminho do ficheiro `.env`.
* **environ** - Dicionário opcional que contém variáveis de ambiente específicas. Por defeito, utiliza `os.environ` se nada for fornecido.
* **prefix** - Uma string `prefix` a ser concatenada em todas as variáveis de ambiente carregadas.
* **ignore_case** - Sinalizador booleano que indica se uma variável de ambiente pode estar em minúsculas. Por defeito,
é falso e transforma internamente todas as variáveis em minúsculas em maiúsculas.
