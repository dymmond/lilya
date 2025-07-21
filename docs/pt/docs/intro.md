# Deployment

Fazer *deployment* de uma aplicação **Lilya** é relativamente fácil.

## O que é um deployment

Fazer *deploy* de uma aplicação significa pensar nos passos necessários para tornar a aplicação disponível para outros utilizarem
fora da sua máquina local e/ou ambiente de desenvolvimento.

Normalmente, fazer *deploy* de APIs web envolve colocar o seu código em máquinas remotas com todos os requisitos necessários
desde memória, CPU, armazenamento até aspetos como a rede. Depende das suas necessidades.

## Estratégias

Existem muitas formas de fazer *deploy* de uma aplicação. Cada caso é único e dependerá de muitos factores que
às vezes não estão nem relacionados com a própria aplicação. Por exemplo, **fundos**.

Pode querer poupar dinheiro **não indo para uma solução cloud**, mas isso também significa mais manutenção pessoal da infraestrutura.

Também pode decidir ir para a **cloud** e usar um fornecedor externo como **AWS, Azure, GCP** ou até um que
é muito bom e também acessível como **render.com** ou **Heroku**. A escolha é realmente sua, pois dependerá das suas necessidades.

O objetivo não é dizer o que fazer, mas dar um exemplo simples no caso de querer usar, por exemplo,
[docker](./docker.md) e a razão é muito simples. **Cada caso é único**.

## Lilya

Foi decidido que não iriamos interferir na forma como as pessoas fazem deploys nem sugerir que existe apenas
uma maneira de o fazer, mas achámos que seria muito útil ter pelo menos um exemplo apenas para ajudar um pouco e
desbloquear algumas potenciais ideias.

Optámos por usar um padrão, [docker](./docker.md).

## Deploying utilizando Pydantic

O Pydantic é fantástico a lidar com a maior parte do trabalho pesado quando se trata de ler variáveis de ambiente e
atribuir, mas há alguns truques a ter em mente.

### Carregar Listas, dicts e tipos complexos

Ao carregar esses elementos nas variáveis de ambiente **é imperativo** que entenda que o Pydantic os lê
como um objecto semelhante ao JSON.

**Examplo**:

```shell
export ALLOWED_HOSTS="https://www.example.com,https://www.foobar.com"
```

Existem várias formas de fazer isso, mas na documentação do Pydantic (e até uma correção), eles recomendam usar o
`parse_env` e tratar a análise lá.

```python
from typing import ClassVar

from lilya.conf.global_settings import Settings


class AppSettings(Settings):
    allowed_hosts: list[str] | str = os.environ.get("ALLOWED_HOSTS", [])

    def __post_init__(self) -> None:
        self.allowed_hosts = self.allowed_hosts.split(",")

```
