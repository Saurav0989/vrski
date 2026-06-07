import os
from sqlmodel import SQLModel, create_engine, Session as DBSession
from sqlalchemy import event

# Default to a local SQLite database in the working directory
DATABASE_URL = os.getenv("VRSKI_DATABASE_URL", "sqlite:///vrski.db")

# check_same_thread and timeout are needed only for SQLite to handle concurrency
connect_args = {"check_same_thread": False, "timeout": 30} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

# Enable WAL mode for SQLite to prevent database lockups during concurrent writes
if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

def init_db():
    from vrski.session.models import Session
    SQLModel.metadata.create_all(engine)

def get_db():
    with DBSession(engine) as db_session:
        yield db_session
