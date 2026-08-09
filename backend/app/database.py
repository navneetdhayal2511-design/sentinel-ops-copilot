from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def migrate_schema() -> None:
    """Best-effort additive migrations for existing SQLite demos."""
    if not settings.database_url.startswith("sqlite"):
        return
    with engine.begin() as conn:
        tables = {
            r[0]
            for r in conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            ).fetchall()
        }
        if "investigations" not in tables:
            return
        cols = {
            r[1]
            for r in conn.execute(text("PRAGMA table_info(investigations)")).fetchall()
        }
        if "citations_json" not in cols:
            conn.execute(
                text("ALTER TABLE investigations ADD COLUMN citations_json TEXT DEFAULT '[]'")
            )
        if "feedback_status" not in cols:
            conn.execute(
                text(
                    "ALTER TABLE investigations ADD COLUMN feedback_status VARCHAR(32) DEFAULT 'pending'"
                )
            )
