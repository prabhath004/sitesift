"""SQLAlchemy declarative base.

Every ORM model must inherit from ``Base`` and must be imported in
``app.models.__init__`` so that Alembic autogenerate can see it.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
