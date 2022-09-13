# Hyperion

## Presentation

Hyperion is the API of an open-source project launched by ÉCLAIR, the computer science association of Ecole Centrale de Lyon. This project aims to provide students of business and engineering schools a digital tool to simplify the association process. In a way, we could say that Hyperion is trying to create a social network for school associations. 

The structure of this project is modular. Hyperion has a core that performs vital functions (authentication, database migration, authorization, etc). The other functions of Hyperion are realized in what we call modules. You can contribute to the project by adding modules if you wish.

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
