from __future__ import annotations
import os
from logging.config import fileConfig
from alembic import context
from sqlalchemy import create_engine, pool
from sqlalchemy.engine.url import make_url
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
# <-- импортируем Base из твоего ORM-модуля
from db_sqlalchemy import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    url = os.getenv("DATABASE_URL") or config.get_main_option(
        "sqlalchemy.url", "")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set and sqlalchemy.url is empty")

    # Нормализуем на psycopg3
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)

    # Добавляем sslmode=require корректно, не глядя на символы в пароле
    if url.startswith("postgresql+psycopg://"):
        p = urlparse(url)
        qs = dict(parse_qsl(p.query, keep_blank_values=True))
        qs.setdefault("sslmode", "require")
        url = urlunparse(p._replace(query=urlencode(qs)))

    return url


def run_migrations_offline() -> None:
    url = get_url()
    u = make_url(url)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        render_as_batch=(u.get_backend_name() == "sqlite"),
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = get_url()
    u = make_url(url)
    connectable = create_engine(
        url, poolclass=pool.NullPool, future=True, pool_pre_ping=True)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            render_as_batch=(u.get_backend_name() == "sqlite"),
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
