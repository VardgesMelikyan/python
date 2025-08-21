# db_sqlalchemy.py
from __future__ import annotations
import os
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy import create_engine, Integer, String, Float, DateTime, Column
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session


def _running_on_render() -> bool:
    # Render web services expose these env vars
    return bool(os.getenv("RENDER_EXTERNAL_URL") or os.getenv("RENDER_EXTERNAL_HOSTNAME"))


def _resolve_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if url:
        # normalize to psycopg3 and require SSL by default
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        if url.startswith("postgresql+psycopg://") and "sslmode=" not in url:
            url += ("&" if "?" in url else "?") + "sslmode=require"
        return url

    # On Render without DATABASE_URL -> fail fast (don’t silently create SQLite)
    if _running_on_render():
        raise RuntimeError(
            "DATABASE_URL не задан в Render. Добавь его в Settings → Environment."
        )

    # Local dev fallback: SQLite
    db_path = Path("data") / "wb.sqlite"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db_path}"


DATABASE_URL = _resolve_database_url()

connect_args = {}
engine_kwargs = dict(pool_pre_ping=True, pool_recycle=300, future=True)
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL, connect_args=connect_args, **engine_kwargs)


class Base(DeclarativeBase):
    pass


SessionLocal = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, future=True)


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, autoincrement=True)
    pid = Column(Integer, unique=True, nullable=False)
    name = Column(String)
    brand = Column(String)
    price = Column(Float)
    rating = Column(Float)
    feedbacks = Column(Integer)
    url = Column(String)
    source = Column(String)
    query = Column(String)
    parsed_at = Column(DateTime(timezone=True))


def init_db() -> None:
    # Создаём таблицы только в локальном SQLite; в Postgres — миграции (Alembic)
    if DATABASE_URL.startswith("sqlite"):
        Base.metadata.create_all(bind=engine)


def upsert_products(rows: list[dict]) -> int:
    if not rows:
        return 0
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:  # type: Session
        affected = 0
        for r in rows:
            pid_val = r.get("pid")
            if not pid_val:
                continue
            obj: Product | None = session.query(
                Product).filter_by(pid=pid_val).first()
            if obj is None:
                obj = Product(pid=pid_val)
                session.add(obj)
            obj.name = r.get("name")
            obj.brand = r.get("brand")
            obj.price = r.get("price")
            obj.rating = r.get("rating")
            obj.feedbacks = r.get("feedbacks")
            obj.url = r.get("url")
            obj.source = r.get("source")
            obj.query = r.get("query")
            obj.parsed_at = now
            affected += 1
        session.commit()
        return affected
