from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
import os
from pathlib import Path

if os.environ.get("WEBAPP_TESTING") == "1":
    _test_db_path = Path("WebApp/test_db.sqlite3")
    # Clean slate each test run
    if _test_db_path.exists():
        try:
            _test_db_path.unlink()
        except Exception:
            pass
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{_test_db_path.as_posix()}"
else:
    SQLALCHEMY_DATABASE_URL = "sqlite:///./DB/Main_DB.db"

class Base(DeclarativeBase):
    pass

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
