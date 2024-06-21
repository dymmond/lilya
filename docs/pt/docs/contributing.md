# Contribuir

Obrigado por mostrar interesse em contribuir para o Lilya. Existem várias maneiras nas quais pode ajudar e contribuir para o projecto.

* Experimente o Lilya e [reporte os bugs e problemas](https://github.com/dymmond/lilya/issues/new) que encontrar.
* [Implemente novas funcionalidades](https://github.com/dymmond/lilya/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22).
* Ajude os outros [reviews the pull requests](https://github.com/dymmond/lilya/pulls).
* Ajude na documentação.
* Utilize as discussões e participe ativamente nelas.
* Torne-se um colaborador ajudando o Lilya a crescer e espalhar a palavra em empresas de todos os tamanhos.
*
## Reportar possíveis bugs e problemas

É natural que se possa encontrar algo que o Lilya deveria dar suporte ou até mesmo experimenciar algum tipo de comportamento inesperado que precise ser corrigido.

A forma como gostamos de fazer as coisas é muito simples, as contribuições devem começar com uma [discussão](https://github.com/dymmond/lilya/discussions).
Os possíveis bugs devem ser criados como "Potential Problem" nas discussões, os pedidos para novas functionalidades pode ser criados como "Ideas".

Podemos então decidir se a discussão precisa ser escalada para um "Problema" ou não.

Ao reportar algo, deve sempre tentar:
* Seja o mais descritivo possível
* Forneça o máximo de evidências possível, algo como:
    * Sistema operativo
    * Versão do Python
    * Dependências instaladas
    * Pedaços de código
    * *Tracebacks*

Evite colocar exemplos extremamente complexos de se perceber e ler.
Simplifique os exemplos o máximo possível para torná-los claros e obter a ajuda necessária.

## Desenvolvimento

Para desenvolver para o Lilya, crie um fork do [repositório do Lilya](https://github.com/dymmond/lilya) no GitHub.

Depois, clone o seu fork com o seguinte comando, substituindo `NOME-DE-UTILIZADOR` pelo seu nome de utilizador do GitHub:

```shell
$ git clone https://github.com/NOME-DE-UTILIZADOR/lilya
```

Lilya também utiliza o [hatch](https://hatch.pypa.io/latest/) para seus ciclos de desenvolvimento, teste e publicação.

Certifique-se de executar:

```shell
pip install hatch
```

### Instalar as dependências do projecto

Não é necessário, pois as dependências são instaladas automaticamente pelo hatch.
Mas se os ambientes devem ser pré-inicializados, isso pode ser feito com `hatch env`

```shell
$ cd lilya
$ hatch env create
$ hatch env create test
$ hatch env create docs
```

!!! Tip
    Esta é a forma recomendada, mas se ainda sentir que deseja ter o seu próprio ambiente virtual e
    todas as bibliotecas instaladas lá, pode sempre executar `scripts/install`.

### Ativar o pre-commit

O projecto vem com uma configuração do pre-commit. Para ativá-lo, basta executar dentro do clone:

```shell
$ hatch run pre-commit install
```

### Executar os testes

Para executar os testes, utilize:

```shell
$ hatch run test:test
```

Porque o Lilya utiliza o pytest, quaisquer argumentos adicionais serão passados.
Mais informações podem ser encontradas na [documentação do pytest](https://docs.pytest.org/en/latest/how-to/usage.html)

Por exemplo, para executar um único teste_script:

```shell
$ hatch run test:test tests/test_encoders.py
```

Para executar a verificação do lint, utilize:

```shell
$ hatch run lint
```

## Documentação

Melhorar a documentação é bastante fácil e ela está localizada dentro da pasta `lilya/docs`.

Para construir toda a documentação:

```shell
$ hatch run docs:build
```

### Documentação em tempo real (servir a documentação)

Durante o desenvolvimento local, há um script que constrói o site e verifica quaisquer alterações, recarregando em tempo real:

```shell
$ hatch run docs:serve
```

A documentação é servida no `http://localhost:8000`.

Se desejar servir num porto diferente:

```shell
$ hatch run docs:serve -p <PORT-NUMBER>
```

Desta forma, pode editar os ficheiros da documentação/fonte e ver as alterações em tempo real.

!!! dica
    Alternativamente, pode executar os mesmos passos que o script faz manualmente.

    Acesse à directoria do idioma. Para a documentação principal em inglês, a localização é `docs/en/`:

    ```console
    $ cd docs/en/
    ```

    De seguida, execute o `mkdocs` nessa directoria:

    ```console
    $ mkdocs serve --dev-addr 8000
    ```

### Estrutura da Documentação

A documentação utiliza o <a href="https://www.mkdocs.org/" class="external-link" target="_blank">MkDocs</a>.

E existem ferramentas/scripts adicionais para lidar com as traduções em `./scripts/docs.py`.

!!! tip
    Não é necessário ver o código dentro de `./scripts/docs.py`, apenas utilize na linha de comando.

Toda a documentação está em formato Markdown na directoria `./docs/pt/`.

Muitos dos tutoriais têm blocos de código.

Na maioria dos casos, esses blocos de código são aplicações completas que podem ser executados tal e qual como estão.

Na realidade, esses blocos de código não são escritos dentro do Markdown, mas são ficheiros Python na directoria `./docs_src/`.

E esses ficheiros Python são incluídos/injetados na documentação a quando a geração gerar o site.

### Traduções

A ajuda com as traduções é MUITO apreciada! E isso não pode ser feito sem a ajuda da comunidade.

Aqui estão os passos para ajudar com as traduções.

#### Tips and guidelines

* Verifique os <a href="https://github.com/dymmond/lilya/pulls" class="external-link" target="_blank">pedidos de pull existentes</a> para o seu idioma. Pode filtrar os pedidos de pull pelas que possuem a etiqueta do seu idioma. Por exemplo, para o espanhol, a etiqueta é <a href="https://github.com/dymmond/lilya/pulls?q=is%3Aopen+sort%3Aupdated-desc+label%3Alang-es+label%3Aawaiting-review" class="external-link" target="_blank">`lang-es`</a>.

* Analise essas solicitações de pull, pedidos alterações ou aprovando-os. Para os idiomas que não falo, aguardarei que outros analisem a tradução antes de fazer o merge.

!!! tip
    Pode <a href="https://help.github.com/en/github/collaborating-with-issues-and-pull-requests/commenting-on-a-pull-request" class="external-link" target="_blank">adicionar comentários com sugestões para alterações</a> a pull requests existentes.

    Consulte a documentação sobre <a href="https://help.github.com/en/github/collaborating-with-issues-and-pull-requests/about-pull-request-reviews" class="external-link" target="_blank">adicionar uma revisão de pull request</a> para aprová-lo ou solicitar alterações.

* Verifique se existe uma <a href="https://github.com/dymmond/lilya/discussions/categories/translations" class="external-link" target="_blank">Discussão no GitHub</a> para coordenar as traduções para o seu idioma. Pode-se subscrever nela e, quando houver um novo pull request para rever, um comentário automático será adicionado à discussão.

* Se traduzir páginas, adicione num único pull request por página traduzida. Isso facilitará em muito a revisão por parte de outros.

* Para verificar o código de duas letras para o idioma que deseja traduzir, pode utilizar a tabela <a href="https://pt.wikipedia.org/wiki/ISO_639-1" class="external-link" target="_blank">Lista de códigos ISO 639-1</a>.

#### Idioma existente

Vamos supor que quer traduzir uma página para um idioma que já possui traduções para algumas páginas, como o espanhol.

No caso do espanhol, o código de duas letras é `es`. Portanto, a directoria para as traduções em espanhol está localizada em `docs/es/`.

!!! dica
    A língua principal ("oficial") é o Inglês, localizado em `docs/en/`.

Agora execute o servidor em tempo real para a documentação em espanhol:

```shell
$ hatch run docs:serve_lang es
```

```shell
// Utilize o comando "live" e passe o código do idioma como argumento da linha de comandos
$ hatch run docs:serve_lang es
```

!!! tip
    Alternativamente, você pode executar os mesmos passos que o script faz manualmente.

    Aceda à directoria do idioma, para as traduções em espanhol está em `docs/es/`:

    ```console
    $ cd docs/es/
    ```

    De seguida, execute o `mkdocs` nessa directoria:

    ```console
    $ mkdocs serve --dev-addr 8000
    ```


Agora pode aceder a <a href="http://127.0.0.1:8000" class="external-link" target="_blank">http://127.0.0.1:8000</a> e ver as suas alterações em tempo real.

Vai verificar que cada idioma tem todas as páginas. No entanto, algumas páginas não estão traduzidas e têm uma caixa de informação no topo, sobre a tradução em falta.

Agora, suponhamos que deseja adicionar uma tradução para a secção [Routing](routing.md){.internal-link target=_blank}.

* Copie o ficheiro em:

```
docs/en/docs/routing/routing.md
```

* Cole-o exatamente no mesmo local, mas para o idioma que deseja traduzir, por exemplo:

```
docs/es/docs/routing/routing.md
```

!!! tip
    Repare que a única alteração no caminho e nome do ficheiro é o código do idioma, de `en` para `es`.

Se aceder ao seu navegador, verá que agora os documentos mostram a sua nova secção (a caixa de informação no topo desapareceu). 🎉

Agora pode traduzir tudo e ver como fica à medida que guarda o ficheiro.

#### Novo Idioma

Vamos supor que deseja adicionar traduções para um idioma que ainda não foi traduzido, nem mesmo algumas páginas.

Vamos supor que quer adicionar traduções para o Crioulo, que ainda não está presente na documentação.

Verificando o link acima, o código para "Crioulo" é `ht`.

O próximo passo é executar o script para gerar uma nova directoria para a tradução:

```shell
// Utilize o comando new-lang, passe o código do idioma como argumento da linha de comandos
$ hatch run docs:new_lang ht

Successfully initialized: docs/ht
```

Agora pode verificar no seu editor de código a directoria recém-criada `docs/ht`.

O comando criou um ficheiro `docs/ht/mkdocs.yml` com uma configuração simples que herda tudo da versão `en`:

```yaml
INHERIT: ../en/mkdocs.yml
site_dir: '../../site_lang/ht'
```

!!! tip
    Também pode simplesmente criar esse ficheiro com esses conteúdos manualmente.

O comando também criou um ficheiro fictício `docs/ht/index.md` para a página principal, pode começar por traduz esse.

Pode continuar com as instruções anteriores para um "Idioma Existente" para esse processo.

Pode fazer o primeiro pull request com esses dois ficheiros, `docs/ht/mkdocs.yml` e `docs/ht/index.md`. 🎉

#### Visualizar o resultado

Como já mencionado anteriormente, pode utilizar o `./scripts/docs.py` com o comando `live` para visualizar os resultados (ou `mkdocs serve`).

Quando terminar, também pode testar tudo como se estivesse online, incluindo todos os outros idiomas.

Para fazer isso, primeiro construa toda a documentação:

```shell
// Utilize o comando "build-all", isto vai demorar um pouco
$ hatch run docs:build
```
Também é possível recolher documentação para uma língua


```shell
// Utilize o comando "build-lang", isto vai demorar um pouco
$ hatch run docs:build_lang your_lang
```

Isto constrói todos os sites independentes do MkDocs para cada idioma, combina-os e gera um *ouput* final localizado em `./site_lang/`.

De seguida, pode servir tudo com o comando `serve`:


```shell
// Use the command "dev" after running "build-all" or "build-lang -l your_lang"
$ hatch run docs:dev

Warning: this is a very simple server. For development, use mkdocs serve instead.
This is here only to preview a site with translations already built.
Make sure you run the build-all command first.
Serving at: http://127.0.0.1:8000
```

## Construir o Lilya

Para construir um pacote localmente, execute:

```shell
$ hatch build
```

Alternativamente, execute:

```shell
$ hatch shell
```

Vai instalar os requisitos e criar um *build* local no seu ambiente virtual.

## Lançamento

*Esta secção destina-se aos maintainers do `Lilya`*.

### Construir o Lilya para publicação

Antes de publicar um novo pacote em produção, algumas considerações precisam ser levadas em conta.

* **Registo de Alterações**
    * Tal como muitos projetos, seguimos o formato do [keepchangelog](https://keepachangelog.com/en/1.0.0/).
    * [Comparar](https://github.com/dymmond/lilya/compare/) `main` com a tag de lançamento e listar as entradas
que são de interesse para os utilizadores da framework.
        * O que **deve** constar no registo de alterações? Funcionalidades adicionadas, alteradas, removidas ou depreciadas e correções de bugs.
        * O que **não deve** constar no registo de alterações? Alterações na documentação, testes ou qualquer coisa não especificada no ponto acima.
        * Certifique-se de que a ordem das entradas está ordenada por importância.
        * Mantenha-o simples.

* *Aumento de Versão*
    * A versão deve estar em `__init__.py` do pacote principal.

#### Publicação

Depois de o PR de `release` ter sido *merged*, crie uma nova [publicação](https://github.com/dymmond/lilya/releases/new)
que inclua:

Exemplo:

Haverá uma publicação da versão `0.2.3`, isto é o que deve incluir.

* Título da publicação: `Version 0.2.3` (sempre em inglês).
* Tag: `0.2.3`.
* A descrição deve ser copiada do changelog e novamente, em inglês.

Depois de criar a publicação, ela deve fazer o upload automático da nova versão para o PyPI. Se algo
não funcionar com o PyPI, o lançamento pode ser feito executando `scripts/release`.
