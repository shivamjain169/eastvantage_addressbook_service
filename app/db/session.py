# Database engine and session factory — provides the get_db dependency for FastAPI routes.

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},  # Required for SQLite multi-threaded access
    echo=False,
)

# autocommit=False and autoflush=False give explicit control over transactions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    # Yields one session per request; always closes the session in the finally block
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
