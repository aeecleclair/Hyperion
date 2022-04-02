# Hyperion

## Creating a virtual environment for Python 3.10.x

### Windows

Create the virtual environment

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
brew install
brew install pyenv-virtualenv
```

Edit `.zhsrc` and add at the end of the file :

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
pip install -r requirement_dev.txt
```

### Production requirements

```bash
pip install -r requirement.txt
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

## Hyperion structure

```
└── app
    ├── main.py
    ├── __init__.py
    ├── crud
    ├── database.py
    ├── models
        └──
    └── schemas
        └──
```

Structure :

``` 
└── app
    ├── main.py
    ├── __init__.py
    ├── crud
    ├── database.py
    ├── models
        └──
    └── schemas
        └──
```