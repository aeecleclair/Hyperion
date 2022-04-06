from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./sql_app.db"
# SQLALCHEMY_DATABASE_URL = "postgresql://user:password@postgresserver/db"

# ATTENTION : Supprimer le echo = True à la fin du dev, celui-ci permet simplement d'obtenir les résultats des query dans la console
engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=True)
# connect_args={"check_same_thread": False},
# future=True,


Base = declarative_base()  # Create a base class for all classes that inherit from it

SessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)  # Create a session factory for the engine
# autocommit=False,
# autoflush=False,
