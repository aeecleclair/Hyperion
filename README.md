# Hyperion

[![codecov](https://codecov.io/gh/aeecleclair/Hyperion/graph/badge.svg?token=Q49AK8EAU1)](https://codecov.io/gh/aeecleclair/Hyperion)

## Presentation

Hyperion is the API of an open-source project launched by ÉCLAIR, the computer science association of Ecole Centrale de Lyon. This project aims to provide students of business and engineering schools a digital tool to simplify the association process. In a way, we could say that Hyperion is trying to create a social network for school associations.

The structure of this project is modular. Hyperion has a core that performs vital functions (authentication, database migration, authorization, etc). The other functions of Hyperion are realized in what we call modules. You can contribute to the project by adding modules if you wish.

## 1. Creating a virtual environment for Python 3.12

<details>
<summary>

### Windows

</summary>

Create the virtual environment

> You need to be in Hyperion main folder

```bash
py -3.12 -m venv .venv
```

If you get an error saying roughly:

```
because the execution of scripts is disabled on this system. Please see "get-help about_signing" for more details.
```

Then in a Powershell, run this to allow scripts executions for your user:

```ps1
Set-ExecutionPolicy Unrestricted -Scope CurrentUser
```

Activate it

```bash
.\.venv\Scripts\activate
```

</details>

<details>
<summary>

### macOS (using Pyenv)

</summary>

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
pyenv virtualenv 3.12.0 hyperion
```

Activate it

```bash
pyenv activate hyperion
```

</details>

## 2. Install dependencies

### About Jellyfish and Rust

If you don't have Rust installed or don't want to install it, decrase the version of `jellyfish` to `0.10.0` in the `requirements-common.txt` file:

```
jellyfish==0.10.0                    # String Matching
```

### About Weasyprint and Pango

Follow the installation steps at https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation.

For Windows, the best way is through MSYS2, Mac users can simply install using Homebrew.

### Install dependencies (for real)

Install the dependencies you'll need using `pip` (the common requirements are included in the development requirements):

```bash
pip install -r requirements-dev.txt
```

If you changed the version of Jellyfish, don't forget to set it back:

```
jellyfish==1.0.4                    # String Matching
```

> If you need to remove all modules from your virtual environnement, delete your `.venv` folder.

## 3. Install and configure a database

Choose either SQLite or PostgreSQL.

### SQLite

#### Advantages

It is a binary.
This means:

- SQLite is lightweight
- It is directly understood by your machine, no special configuration is needed.

#### Disadvantages

Being so light, it does not support some features nowadays common for relational databases:

- Drop your database on every migration: Alembic uses features incompatible with SQLite

#### Installation and configuration

There is nothing to do, it works out of the box.

### PostgreSQL

#### Advantages

Its advantages are many:

- Very powerful database: it supports all the features you'll ever need.
- Used in production for Hyperion.
- Widely used in production in enterprise-grade services: useful competence on your résumé.
- Supports migrations with Alembic.
- A powerful CLI tool.

#### Disadvantages

None (not so heavy, configuration not so hard).

#### Configuration

<details>
<summary>

##### Without Docker: native binaries

</summary>

1. Download the installer: https://www.enterprisedb.com/downloads/postgres-postgresql-downloads
2. Launch it and trust the wizard
   - Keep the default folders and ports, install it all, etc...
   - ...but put a concise password you'd remember, choose your language
   - Don't use the "Stack Builder" (not needed)
3. On Windows: in your path, add `C:\Program Files\PostgreSQL\17\bin` and `C:\Program Files\PostgreSQL\17\lib` (if you installed Postgres 17 in that location)
4. Create a database named `hyperion`

```sh
psql -U postgres -c "create database hyperion;"
```

> [!TIP]
> SQL keywords are case-insensitive by convention.
> No need to write `CREATE DATABASE hyperion;`

Now your Hyperion database can be explored by hand (as the `postgres` user, using your password you chose) with:

```bash
psql -U postgres -d hyperion
```

then running SQL or Postgres commands in this shell, or

```bash
psql -U postgres -d hyperion -c "select firstname from core_user;"
```

</details>

<details>
<summary>

##### With Docker

</summary>

> [!WARNING]
> Work in progress

```
services:
  hyperion-db:
    image: postgres:15.1
    container_name: hyperion-db
    restart: unless-stopped
    healthcheck:
      test: [ "CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}" ]
      interval: 5s
      timeout: 5s
      retries: 5
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_HOST: ${POSTGRES_HOST}
      POSTGRES_DB: ${POSTGRES_DB}
      PGTZ: ${POSTGRES_TZ}
    ports:
      - 5432:5432
    volumes:
      - ./hyperion-db:/var/lib/postgresql/data
```

</details>

## 4. Complete the dotenv (`.env`) and the `config.yaml`

> [!IMPORTANT]
> Copy the `.env.template` file in a new `.env` file, likewise copy `config.template.yaml` in a new `config.yaml`.

> [!TIP]
> These template files were carefully crafted to work for you with minimal personal changes to bring, and some preconfigured services.

For later reference, these settings are documented in [app/core/config.py](./app/core/config.py).
Check this file to know what can and should be set using these two files.

### `.env`

The `.env` contains environment variables which need to be accessed by the OS or by other services, such as the database.

#### With SQLite

Again there's nothing to do.

<details>
<summary>

#### With PostgreSQL

</summary>

Set your user, password, host and db.

For instance, with the installer you should have something like:

```sh
POSTGRES_USER="postgres"
POSTGRES_PASSWORD=""
POSTGRES_HOST="localhost"
POSTGRES_DB="hyperion"
```

While with Docker you should have rather something like:

```sh
POSTGRES_USER="hyperion"
POSTGRES_PASSWORD=""
POSTGRES_HOST="hyperion-db"
POSTGRES_DB="hyperion"
```

</details>

### `config.yaml`

The `config.yaml` contains environment variables that are internal to the Python runtime _because_ they are only used in the Python code.

1. `ACCESS_TOKEN_SECRET_KEY`: **Uncomment it**.
   You can generate your own if you want, or just change a couple characters, or leave it as it is.
2. `RSA_PRIVATE_PEM_STRING`: **Uncomment it**.
   You can generate your own if you want, or just change a couple characters, or leave it as it is.
3. `SQLITE_DB`: **tells Hyperion whether to use SQLite or PostgreSQL**.
   - If you use **SQLite**: this field should be a (relative) filename, by default we named it `app.db`, you can change this name.
     Hyperion will create this file for you and use it as the database.
     Any PostgreSQL-related configuration will be ignored.
   - If you use **PostgreSQL**: empty this field.
     Hyperion will fallback to PostgreSQL settings.
4. `USE_FACTORIES`: `True` by default, factories seed your database, if empty, with mocked data.
   This is useful on SQLite to repopulate your new database after dropping the previous one.

## 5. Launch the API

> [!WARNING]
> Beforehand, check that your venv is activated.

### Using VS Code

1. In the activity bar (the leftmost part), click the _Run and Debug_ icon (the play button).
2. Click the green play button.

Check that your Hyperion instance is up and running by navigating to http://localhost:8000/information.

### Using the command-line interface

```bash
fastapi dev
```

Check that your Hyperion instance is up and running by navigating to http://localhost:8000/information.

## 6. Create your own user

There are many ways to do so, ranked here from easiest (GUI only) to hardest (CLI only).
Note that registration and activation are distinct steps, so for fun you may register one way and activate your account another way.

<details>
<summary>

### With CalypSSO

</summary>

#### Registering your account

Go to http://localhost:8000/calypsso/register and type a valid email address to register (start the creation of) your account.

#### Activating your account

Go back to the shell running your Hyperion instance, in the logs look for a link looking like http://localhost:3000/calypsso/activate?activation_token=12345.
Open it and activate (end the creation of) your account.

</details>

<details>
<summary>

### With Titan

</summary>

1. Click "_Se connecter_" on the login page: you land CalypSSO's login page.
2. Click "_Créer un compte_" and create your account using CalypSSO as above.

</details>

<details>
<summary>

### Using the API through the swagger

</summary>

#### Registering your account

1. Go to http://localhost:8000/docs: this is called the _swagger_, a web interface to interact with the API, it is a layer on top of the "automatic documentation" (the _OpenAPI specification_) generated by FastAPI at http://localhost:8000/openapi.json.
2. Search `/users/create`.
3. Open it, click "Try it out".
4. Fill in your email address, and click "Execute".

#### Activating your account

1. Go back to the shell running your Hyperion instance, in the logs look for a link looking like http://localhost:3000/calypsso/activate?activation_token=12345.
2. Copy this activation token.
3. Go again on the swagger and search `/users/activate`.
4. Open it, click "Try it out".
5. Fill in your information, using the `activation_token` you copied (click "Schema" next to "Edit Value" so see what fields are optional), and click "Execute".

</details>

<details>
<summary>

### Using the API in command line

</summary>

> [!TIP]
> On Windows, `curl` is different.
> To get the same results as on Linux and MacOS:
>
> - either replace `curl` with `curl.exe`
> - or run the `curl` commands below in a bash (using WSL or using Git Bash)

#### Registering your account

```bash
curl --json '{"email": "prenom.nom@etu.ec-lyon.fr"}' http://localhost:8000/users/create
```

#### Activating your account

1. Go back to the shell running your Hyperion instance, in the logs look for a link looking like http://localhost:3000/calypsso/activate?activation_token=12345.
2. Copy this activation token.
3. Use this `activation_token` in:

```bash
curl --json '{
    "name": "<Name>",
    "firstname": "<Firstname>",
    "nickname": "<Nickname>",
    "activation_token": "<ActivationToken>",
    "password": "<Password>",
    "birthday": "<2019-08-24>",
    "phone": "<Phone>",
    "promo": 0,
    "floor": ""
}' http://localhost:8000/users/activate
```

</details>

## 7. Make the first user admin

> [!WARNING]
> This may not work if you ran the factories

If there is exactly one user in the database, you can make it admin using the following command:

```bash
curl -X POST http://localhost:8000/users/make-admin
```

---

<details>
<summary>

# Beyond initial configuration

</summary>

## Install Docker or an equivalent

Install docker and the compose plugin (https://docs.docker.com/compose/install/)

`docker-compose.yaml` includes the minimal settings required to run Hyperion using docker compose.

> During dev, `docker-compose-dev.yaml` can be used to run the database, the redis server etc... If you really want to run the project without docker, you can do it but you will have to install the database, redis, etc ... yourself or disable corresponding features in the .env file (which is not recommended).

## Linting and formating

To lint and format, we currently use `Ruff`. We also use `Mypy` for the type checking.

Before each PR or git push you will need to run `ruff check --fix && ruff format` in order to format/lint your code and `mypy .` in order to verify that there is no type mismatch.

## Use Alembic migrations

See [migrations README](./migrations/README)

> [!WARNING]
> On SQLite databases, you have to drop the database and recreate it to apply the new DDL.

## OpenAPI specification

API endpoints are parsed following the OpenAPI specifications at `http://127.0.0.1:8000/openapi.json`.

A Swagger UI is available at `http://127.0.0.1:8000/docs`. For authentication to work, a valid `AUTH_CLIENT` must be defined in the `.env`, with `http://127.0.0.1:8000/docs/oauth2-redirect` as the redirect URI, and `scope=API` must be added to the authentication request.

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

</details>
