# Create a module on Hyperion



## What is a module ?

A module can be define as a fonctionnality which is linked to the core.

## Step 1 : Create the models

### Table

To communicate with the database we use the SQL toolkit **SQLAlchemy**. 

```python
from sqlalchemy import Column, ForeignKey, Integer, String, Date, DateTime
from sqlalchemy.orm import relationship
```

This step is close to basic SQL. Here is an example :

```python
class CoreUser(Base):
    __tablename__ = "core_user"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    firstname = Column(String, nullable=False)
    nickname = Column(String)
    birthday = Column(Date)
    promo = Column(Integer)
    phone = Column(Integer)
    floor = Column(String, nullable=False)
    created_on = Column(DateTime)
    password = Column(String, nullable=False) 
```

The creation of the table rely in creating a class (with camel case notation) with an attribut `__tablename__` which is the name of the table (with snace case notation).

Then, we create the column and indicate the type of object we are going to stock. As you can see, the method Column take arguments. The most useful are :

* `primary_key` : True if the field is a primary_key
* `nullable` : False if the field can't be None
* `default` : to set a default value of the field
* `index` :

### Relationship

The biggest difference with classic SQL appear with the relationship feature. In SQL you link table by joining them, with SQLAlchemy you link the table when you initialize them. 

There is four case :

* Many to Many
* Many to One
* One to Many
* One to One

## Step 2 : Create the schemas

## Step 3 : Create the CRUD operations

## Step 4 : Endpoints

