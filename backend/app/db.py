import ssl

import certifi
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import ROOT_DIR, settings


def _build_engine():
    if settings.database_url or settings.tidb_host:
        url = settings.database_url or URL.create(
            "mysql+pymysql",
            username=settings.tidb_user,
            password=settings.tidb_password,
            host=settings.tidb_host,
            port=settings.tidb_port,
            database=settings.tidb_db_name,
            query={"charset": "utf8mb4"},
        )
        connect_args = {"check_same_thread": False} if str(url).startswith("sqlite") else {}
        if str(url).startswith("mysql"):
            ctx = ssl.create_default_context(cafile=settings.tidb_ssl_ca or certifi.where())
            connect_args["ssl"] = ctx
        return create_engine(url, pool_pre_ping=True, pool_recycle=300, connect_args=connect_args)
    path = ROOT_DIR / "backend" / "movpick.sqlite3"
    return create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})


engine = _build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
