# Utilizar o docker

O que é o Docker? Citando-os

> O Docker é um conjunto de produtos de plataforma como serviço que utilizam virtualização ao nível do sistema operativo
> para fornecer software em pacotes chamados containers.

## A forma convencional

Quando se faz um *deployment*, geralmente precisa-se de:

* Decidir quantos ambientes vai se implementar (teste, staging, produção...)
* Preparar os requisitos.
* Preparar possíveis variáveis de ambiente.
* Preparar *secrets* para serem passados para a aplicação.
* Possivelmente, preparar os acessos à base de dados através dessas mesmas variáveis de ambiente.
* Orquestração.
* ...

E no final, muita esperança de que tudo funcione perfeitamente em cada ambiente, desde que sejam exatamente iguais.

**Isto é muito bom mas susceptível a erros humanos**.

## A abordagem do Docker

Ao utilizar o Docker, ainda é necessário pensar na infraestrutura e nos recursos para a aplicação, mas reduz a
necessidade de instalar os mesmos binários em cada ambiente, uma vez que eles serão geridos por um **container**.

Imagine um container como um ficheiro zip. Simplesmente reúne tudo o que é necessário para que o Lilya funcione num único
lugar e "zipa" isso, o que neste caso significa "dockerizar" a aplicação.
Isto significa que em cada ambiente os binários serão **exatamente os mesmos** e não dependerão de seres humanos, reduzindo a complexidade.

## Exemplo do Lilya e Docker

Vamos supor que queremos implantar uma aplicação simples do **Lilya** utilizando o Docker.
Assumindo que os recursos externos já estão a ser tratados e geridos.

Vamos utilizar:

* [Configuração do Nginx](#nginx) - Servidor web.
* Supervisor - Gestor de processos.
* Aplicação Lilya dockerizada.
**Suposições**:

* Todas as configurações serão colocadas numa pasta chamada `/deployment`.
* A aplicação terá uma estrutura de pastas simples

    ```txt
    .
    ├── app
    │   ├── __init__.py
    │   └── main.py
    ├── Dockerfile
    ├── deployment/
    │   ├── nginx.conf
    │   └── supervisor.conf
    └── requirements.txt
    ```

* O ficheiro de requisitos

    ```txt
    lilya
    uvicorn
    nginx
    supervisor
    ```

**Como mencionado nestes documentos, estaremos a utilizar o uvicorn nos exemplos, mas é livre de usar o que quiser**

### A aplicação

Vamos começar com uma aplicação simples, de um único ficheiro, apenas para enviar um hello word.

```python title='app/main.py'
{!> ../../../docs_src/deployment/app.py !}
```

### Nginx

O Nginx é um servidor web que também pode ser usado como um *reverse proxy*, balanceador de carga, proxy de email e cache HTTP.

Encontrará mais detalhes sobre o Nginx na [a documentação oficial](https://www.nginx.com/) e como utilizá-lo.

Vamos começar a construir a nossa simples configuração nginx.

```nginx
{!> ../../../docs_src/deployment/nginx.conf !}
```
Criamos uma configuração simples do `nginx` com algum nível de segurança para garantir que protegemos a aplicação em todos os níveis.

### Supervisor

O Supervisor é um gestor de processos simples, mas poderoso, que permite monitorizar e controlar vários processos em sistemas
operativos semelhantes ao UNIX.

[A documentação deles](http://supervisord.org/) irá ajudá-lo a entender melhor como utilizá-lo.

Agora é hora de criar uma configuração para o supervisor.

```ini
{!> ../../../docs_src/deployment/supervisor.conf !}
```

Parece complexo e extenso, mas vamos traduzir o que esta configuração está realmente a fazer.

1. Cria as configurações iniciais para o `supervisor` e `supervisord`.
2. Declara as instruções de como iniciar o [nginx](#nginx).
3. Declara as instruções de como iniciar o `uvicorn` e a aplicação lilya.

### Dockefile

O ficheiro Dockerfile é onde se coloca todas as instruções necessárias para iniciar a aplicação assim que for construída,
por exemplo, iniciar o [supervisor](#supervisor) que irá então iniciar todos os processos declarados na sua configuração.

```{ .dockerfile .annotate }
# (1)
FROM python:3.9

# (2)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libatlas-base-dev gfortran nginx supervisor nginx-extras

# (3)
WORKDIR /src

# (4)
COPY ./requirements.txt /src/requirements.txt

# (5)
RUN pip install --no-cache-dir --upgrade -r /src/requirements.txt

# (6)
COPY ./app /src/app

COPY deployment/nginx.conf /etc/nginx/
COPY deployment/nginx.conf /etc/nginx/sites-enabled/default
COPY deployment/supervisord.conf /etc/

# (7)
CMD ["/usr/bin/supervisord"]
```

1. Comece a partir de uma imagem base oficial do Python.
2. Instale os requisitos mínimos para executar o Nginx e o Supervisor.
3. Defina a directoria atual como `/src`.

    É aqui que irá colocar o `requirements.txt` e a directoria `app`.

4. Copie os requisitos para o seu projecto.

    Você deve copiar apenas os requisitos e não o restante do código, e a razão para isso é o **cache** do Docker. Se o arquivo não mudar com muita frequência, ele será armazenado em cache e na próxima vez que você precisar reconstruir a imagem, ele não repetirá as mesmas etapas o tempo todo.

5. Instale os requisitos.

    O `--no-cache-dir` é opcional. Pode simplesmente adicioná-lo para informar o pip para não armazenar em cache os pacotes, localmente.

    O `--upgrade` é para garantir que o pip atualiza os pacotes instalados para a versão mais recente.

6. Copie o `./app` para a directoria `/src`.

    Também copie os ficheiros `nginx.conf` e `supervisor.conf` previamente criados para as respectivas pastas do sistema.

7. Indique ao `supervisor` para começar a ser executado. O sistema usará o ficheiro `supervisor.conf` criado e acionará
as instruções declaradas, como iniciar o Nginx e o Uvicorn.
## Construir a imagem Docker

Com o [Dockerfile](#dockefile) criado, agora é hora de construir a imagem.

```shell
$ docker build -t myapp-image .
```

### Testar a imagem localmente

Pode testar a sua imagem localmente antes de implementar e verificar se funciona como desejado.

```shell
$ docker run -d --name mycontainer -p 80:80 myapp-image
```

### Verificar

Após [construir a imagem](#construir-a-imagem-docker) e [iniciar localmente](#testar-a-imagem-localmente),
pode então verificar se ela funciona como desejado.

**Examplo**:

* [http://127.0.0.1/](http://127.0.0.1/)
* [http://127.0.0.1/users/5?q=somequery](http://127.0.0.1/users/5?q=somequery)

## Importante

Foi fornecido um exemplo de como construir alguns ficheiros semelhantes aos necessários para uma determinada implementação.

**Deve sempre verificar e alterar qualquer um dos exemplos para se adequar às suas necessidades e garantir que funcione para si**
