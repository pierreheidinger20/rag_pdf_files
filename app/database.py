import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False
)


def init_db():
    with engine.connect() as connection:
        connection.execute(
            text("CREATE EXTENSION IF NOT EXISTS vector")
        )
        connection.commit()