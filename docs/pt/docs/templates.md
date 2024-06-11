# Templates

O Lilya não está intrinsecamente ligado a nenhum mecanismo de modelagem específico, mas o Jinja2 destaca'se como uma excelente escolha devido às suas origens comprovadas e ampla adoção no mundo Python.

## Jinja2Template

Isso é o que Lilya traz por defeito e permite servir HTML por meio dos *handlers*.

```python
from lilya.templating import Jinja2Template
```

### Parâmetros

- `directory`: Uma string, [os.Pathlike][pathlike], ou uma lista de strings ou [os.Pathlike][pathlike] indicando um caminho para uma directoria.
- `env`: Qualquer instância diferente de `jinja2.Environment` *(Opcional)*.
- `**options`: Argumentos de palavra-chave adicionais para passar ao ambiente Jinja2.

## Uso do Jinja2Template

O Lilya traz uma configuração pré-configurada do `Jinja2Template` que provavelmente será o que desejará usar. Caso queira um `jinja2.Enviroment` diferente,
isso também pode ser passado ao instanciar o `Jinja2Template`.

```python
{!> ../../../docs_src/templates/template.py !}
```

### Parâmetros de resposta dos modelos

A função `get_template_response` espera os seguintes argumentos:

- `request`: (obrigatório): O objecto de *request* HTTP.
- `name`: (obrigatório): O nome da template a ser renderizada.

Quaisquer argumentos ou argumentos de palavra-chave adicionais fornecidos serão passados diretamente para a template como contexto.
Isto permite incluir dados dinâmicos no processo de renderização da template. Pode passar esses argumentos como argumentos de palavra-chave ou argumentos posicionais, dependendo de sua preferência.

!!! warning
    É imperativo incluir a instância de *request* recebida como parte do contexto da template.

O contexto da template Jinja2 incorpora automaticamente uma função `url_for`, permitindo a criação correta de links para outras páginas dentro da aplicação.

Por exemplo, ficheiros estáticos podem ser vinculados a partir de templates HTML:

```jinja
{!> ../../../docs_src/_shared/jinja.html !}
```

Caso deseje utilizar [filtros personalizados][jinja2], será necessário atualizar a propriedade `env` do `Jinja2Template`:

```python
{!> ../../../docs_src/templates/custom.py !}
```

## O `jinja2.Environment`

Lilya aceita uma instância preconfigurada de [jinja2.Environment](https://jinja.palletsprojects.com/en/3.0.x/api/#api) passando-a dentro do atributo `env` ao instanciar o `Jinja2Template`.

```python
{!> ../../../docs_src/templates/env.py !}
```

## Processadores de Contexto

Um processador de contexto é uma função que retorna um dicionário a ser incorporado num contexto da template. Cada função recebe apenas um argumento, `request`,
e deve retornar um dicionário a ser adicionado ao contexto.

Um caso de uso típico para processadores da template é aprimorar o contexto da template com variáveis compartilhadas.

```python
{!> ../../../docs_src/templates/ctx.py !}
```

### Registrando Processadores de Contexto

Para registrar processadores de contexto, passe-os para o argumento `context_processors` da classe `Jinja2Template`.

```python
{!> ../../../docs_src/templates/ctx_register.py !}
```

## Ambiente Jinja2 Personalizado

`Jinja2Template` aceita todas as opções suportadas pelo `Environment` do Jinja2. Isto concede um maior controlo sobre a instância de `Environment` criada pelo Lilya.

Para a lista de opções disponíveis para `Environment`, consulte a documentação do Jinja2 [aqui](https://jinja.palletsprojects.com/en/3.0.x/api/#jinja2.Environment).

```python
{!> ../../../docs_src/templates/custom_jinja.py !}
```

## Renderização da Template Assíncrona

Embora o Jinja2 suporte a renderização assíncrona de templates, é aconselhável evitar a inclusão de lógica em templates que acionem consultas de base de dados ou outras operações de I/O.

Uma prática recomendada é garantir que os endpoints lidem com todas as operações de I/O. Por exemplo, execute consultas de base de dados dentro da *view* e inclua os resultados finais no contexto. Esta abordagem ajuda a manter as templates focados na lógica de apresentação, em vez de operações de I/O.

[jinja2]: https://jinja.palletsprojects.com/en/3.0.x/api/?highlight=environment#writing-filters
[pathlike]: https://docs.python.org/3/library/os.html#os.PathLike
