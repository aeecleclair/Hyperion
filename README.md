# Hyperion

[![codecov](https://codecov.io/gh/aeecleclair/Hyperion/graph/badge.svg?token=Q49AK8EAU1)](https://codecov.io/gh/aeecleclair/Hyperion)

## Presentation

Hyperion is the API of an open-source project launched by ÉCLAIR, the computer science association of Ecole Centrale de Lyon. This project aims to provide students of business and engineering schools a digital tool to simplify the association process. In a way, we could say that Hyperion is trying to create a social network for school associations.

The structure of this project is modular. Hyperion has a core that performs vital functions (authentication, database migration, authorization, etc). The other functions of Hyperion are realized in what we call modules. You can contribute to the project by adding modules if you wish.

## Creating a virtual environment for Python 3.11.x

### Windows

Create the virtual environment

> You need to be in Hyperion main folder

```bash
py -3.11 -m venv .venv
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
pyenv virtualenv 3.11.0 hyperion
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

> If you need to remove all modules from your virtual environnement, you may use the following command with caution
>
> ```bash
> pip freeze | xargs pip uninstall -y
> ```

## Linting and formating

To lint and format, we currently use `Ruff`. We also use `Mypy` for the type checking.

Before each PR or git push you will need to run `ruff check --fix && ruff format` in order to format/lint your code and `mypy .` in order to verify that there is no type mismatch.

## Complete the dotenv (`.env`)

> Hyperion settings are documented in [app/core/config.py](./app/core/config.py).
> Check this file to know what can and should be set using the dotenv.

`SQLITE_DB` is None by default. If you want to use SQLite (if you don't use docker or don't have a postgres running), set it with the name of the db file (`app.db` for example).

`ACCESS_TOKEN_SECRET_KEY` should be a strong random key, which will be used to sign JWT tokens

`RSA_PRIVATE_PEM_STRING` will be used to sign JWS tokens

```bash
# Generate a 2048 bits long PEM certificate and replace newlines by `\n`
openssl req -newkey rsa:2048 -nodes -x509 -days 365 | sed 's/$/\\n/g' | tr -d '\n'
# If you only want to generate a PEM certificate and save it in a file, th following command may be used
# openssl req -newkey rsa:2048 -nodes -keyout key.pem -x509 -days 365 -out certificate.pem
```

`REDIS` may be left blank to disable Redis during development
Numerical values are example, change it to your needs

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

## Launch the API

```bash
fastapi dev app/main.py
```

## Use Alembic migrations

See [migrations README](./migrations/README)

Warning : on SQLite databases, you have to drop the database and recreate it to apply the new DDL.

## OpenAPI specification

API endpoints are parsed following the OpenAPI specifications at `http://127.0.0.1:8000/openapi.json`.

A Swagger UI is available at `http://127.0.0.1:8000/docs`. For authentication to work, a valid `AUTH_CLIENT` must be defined in the `.env`, with `http://127.0.0.1:8000/docs/oauth2-redirect` as the redirect URI, and `scope=API` must be added to the authentication request.

## Create the first user

You can create the first user either using Titan or calling the API directly.

> You need to use an email with the format `...@etu.ec-lyon.fr` or `...@ec-lyon.fr`

To activate your account you will need an activation token which will be printed in the console.

### With Titan

Press "Créer un compte" on the first page and follow the process.

### Using the API directly

Create the account:

```bash
curl --location 'http://127.0.0.1:8000/users/create' \
--header 'Content-Type: application/json' \
--data-raw '{
    "email": "<...>@etu.ec-lyon.fr",
    "account_type": "39691052-2ae5-4e12-99d0-7a9f5f2b0136"
}'
```

Activate the account:

```bash
curl --location 'http://127.0.0.1:8000/users/activate' \
--header 'Content-Type: application/json' \
--data '{
    "name": "<Name>",
    "firstname": "<Firstname>",
    "nickname": "<Nickname>",
    "activation_token": "<ActivationToken>",
    "password": "<Password>",
    "birthday": "<2019-08-24>",
    "phone": "<Phone>",
    "promo": 0,
    "floor": ""
}'
```

## Make the first user admin

If there is exactly one user in the database, you can make it admin using the following command:

```bash
curl --location --request POST 'http://127.0.0.1:8000/users/make-admin'
```

## Install docker or an equivalent

Install docker and the compose plugin (https://docs.docker.com/compose/install/)

`docker-compose.yaml` includes the minimal settings required to run Hyperion using docker compose.

> During dev, `docker-compose-dev.yaml` can be used to run the database, the redis server etc... If you really want to run the project without docker, you can do it but you will have to install the database, redis, etc ... yourself or disable corresponding features in the .env file (which is not recommended).

---

## Configure Firebase notifications

Hyperion support push notification using Firebase Messaging service.

To enable the service:

1. Add `USE_FIREBASE=true` to dotenv file
2. Create a service account on Firebase console:
   1. Go to [Google cloud, IAM and administration, Service account](https://console.cloud.google.com/iam-admin/serviceaccounts) and add a new Service Account with Messaging API capabilities.
   2. Choose _Manage keys_ and create a new JSON key.
   3. Rename the file `firebase.json` and add it at Hyperion root

## Use websocket

When using multiples workers, a Redis server must be configured to broadcast messages between workers.

## Google API usage

Hyperion can use Google API to run App Script and upload files to Google Drive.
See [app/core/google_api/README.md](./app/core/google_api/README.md) for more information.

---

## Hyperion deployment

For production we encourage to use multiple Uvicorn workers. You can use our [docker image](./Dockerfile) and [docker-compose file](./docker-compose.yaml) files to run Hyperion with Unicorn.

You should use our [init file](./init.py) to ensure that database initialization and migrations are only run once.
