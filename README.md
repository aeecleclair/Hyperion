# Hyperion

## Presentation

Hyperion is the API of an open-source project launched by ÉCLAIR, the computer science association of Ecole Centrale de Lyon. This project aims to provide students of business and engineering schools a digital tool to simplify the association process. In a way, we could say that Hyperion is trying to create a social network for school associations. 

The structure of this project is modular. Hyperion has a core that performs vital functions (authentication, database migration, authorization, etc). The other functions of Hyperion are realized in what we call modules. You can contribute to the project by adding modules if you wish.

## Install docker or an equivalent
Install docker and the compose plugin (https://docs.docker.com/compose/install/)

> During dev docker is used to run the database, the redis server etc ... If you really want to run the project without docker, you can do it but you will have to install the database, redis, etc ... yourself or disable some features in the .env file (which is not recommended).

## Creating a virtual environment for Python 3.10.x

### Windows

Create the virtual environment

> You need to be in Hyperion main folder

```bash
py -3.10 -m venv .venv
```

Activate it

```bash
.\.venv\Scripts\activate
```

### macOS (using Pyenv)

Install Pyenv

```bash
brew install pyenv
brew install pyenv-virtualenv
```

Edit `~/.zhsrc` and add at the end of the file :

```bash
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
```

Create the virtual environment

```bash
pyenv virtualenv 3.10.3 hyperion
```

Activate it

```bash
pyenv activate hyperion
```

## Install dependencies

### Development requirements

```bash
pip install -r requirements-dev.txt
```

### Production requirements

```bash
pip install -r requirements.txt
```

> We need to add
> pep8-naming
> Security requirements
> Use a spell checker

> Pip freeze
>
> ```bash
> pip freeze > requirements.txt
> pip install -r requirements.txt
> ```

> Remove all modules
>
> ```bash
> pip freeze | xargs pip uninstall -y
> ```

## Launch the API

```bash
uvicorn app.main:app --reload
```

## Complete the dotenv (`.env`)

> Hyperion settings are documented in [app/core/config.py](./app/core/config.py).
> Check this file to know what can and should be set using the dotenv.

`TESTING` is set to False by default. If you want to run the tests, set it to True.

`SQLITE_DB` is set to False by default. If you want to use SQLite (if you don't use docker and don't have a postgres running), set it to True.

`ACCESS_TOKEN_SECRET_KEY`

```python
from app.core.security import generate_token
generate_token(64)
```

`RSA_PRIVATE_PEM_STRING`

```bash
# Generate a 2048 bits long PEM certificate and replace newlines by `\n`
openssl req -newkey rsa:2048 -nodes -x509 -days 365 | sed 's/$/\\n/g' | tr -d '\n'
# If you only want to generate a PEM certificate and save it in a file, th following command may be used
# openssl req -newkey rsa:2048 -nodes -keyout key.pem -x509 -days 365 -out certificate.pem
```

`REDIS`: Numerical values are example, change it to your needs

```python
REDIS_HOST = "localhost" #May be left at "" during dev if you don't have a redis server running
REDIS_PORT = 6379
#REDIS_PASSWORD = "pass" Should be commented during development to work with docker-compose-dev, and set in production
REDIS_LIMIT = 1000
REDIS_WINDOW = 60
```

`POSTGRES`: This section will be ignored if `SQLITE_DB` is set to True.
```python
POSTGRES_HOST = "localhost"
POSTGRES_USER = "hyperion"
POSTGRES_PASSWORD = "pass"
POSTGRES_DB = "hyperion"
```
