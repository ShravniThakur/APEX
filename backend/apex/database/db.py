"""Engine, session factory, and declarative base."""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from ..config import DATABASE_URL


class Base(DeclarativeBase):
    pass


# pool_pre_ping: test a pooled connection before handing it out, so a connection the
# DB server has since closed (e.g. after the long synchronous /pipeline/run-all) is
# transparently replaced instead of raising "server closed the connection unexpectedly".
# pool_recycle: proactively retire connections older than 30 min.
engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True, pool_recycle=1800)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)
