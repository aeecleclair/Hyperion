# Generating migrations

The project use Alembic migrations to manage database structure evolutions.

When the database does not exist, SQLAlchemy will create a new database with an up to date structure. When the database already exist, migrations must be run to update the structure.

### Run migrations

These [migration files](./migrations/versions/) are automatically run before Hyperion startup.

They can also be run manually using the following command:

```bash
alembic upgrade head
```

> If you want to force Alembic to consider your database structure is up to date, you can use the following command:
>
> ```bash
> alembic stamp head
> ```
>
> If the database stamp is a migration that does not exist anymore, you can use the following command to
> force Alembic to consider your database structure is up to date
>
> ```bash
> alembic stamp --purge head
> ```

### Write migration files

To create a new migration file, use the following command:

```bash
alembic revision --autogenerate -m "Your message"
```

Files must be names with the following convention: `number-message.py

## Best practices

For migrations to be compatible with SQLite, `alter` commands should be wrapped in a [`batch_alter_table` context manager](https://alembic.sqlalchemy.org/en/latest/batch.html).

## Code snippets

### Add a value to an Enum

```python
with op.batch_alter_table("table_name") as batch_op:
    batch_op.alter_column(
        "field_name",
        existing_type=sa.VARCHAR(length=23),
        type_=sa.Enum(
            "value1",
            "value2",
            "newvalue1",
            "newvalue2",
            name="enum_name",
        ),
        existing_nullable=False,
    )
```

### Server default

**Boolean**
You need to use `server_default=sa.sql.false()`
