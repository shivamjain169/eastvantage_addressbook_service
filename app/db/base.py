# Shared SQLAlchemy declarative base — all ORM models inherit from this class.

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
