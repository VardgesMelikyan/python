# db_sqlalchemy.py
from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime, timezone

from sqlalchemy import create_engine, Integer, String, Float, DateTime, Column
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

# 1) Путь к SQLite-файлу (data/wb.sqlite). Папку создаём, если её нет.
DB_PATH = Path("data") / "wb.sqlite"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# 2) URL подключения к БД.
#    По умолчанию — SQLite, но можно переопределить переменной окружения DATABASE_URL
#    Примеры:
#    - SQLite:  sqlite:///data/wb.sqlite
#    - Postgres: postgresql+psycopg://user:pass@localhost:5432/wb
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")

# 3) Движок SQLAlchemy — точка входа к БД.
#    echo=False — не засоряем консоль SQL-запросами (для дебага можно True)
engine = create_engine(DATABASE_URL, echo=False, future=True)

# 4) Базовый класс для декларативных моделей ORM.


class Base(DeclarativeBase):
    pass


# 5) Фабрика сессий. Сессия — это «единица работы» с БД (транзакция, кэш объектов).
SessionLocal = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, future=True)


# ---------- Модель ----------

class Product(Base):
    """
    ORM-модель для таблицы products.
    Каждое поле — это Column(..), типы — из sqlalchemy.
    """
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)    # PK
    pid = Column(Integer, unique=True, nullable=False)  # ID товара из WB
    name = Column(String)
    brand = Column(String)
    price = Column(Float)
    rating = Column(Float)
    feedbacks = Column(Integer)
    url = Column(String)
    # откуда получили (search / category / ...)
    source = Column(String)
    query = Column(String)  # поисковая фраза
    # когда мы это спарсили (UTC)
    parsed_at = Column(DateTime(timezone=True))


# ---------- Инициализация схемы ----------

def init_db() -> None:
    """
    Создаёт таблицы в БД, если их ещё нет.
    Base.metadata хранит схему всех моделей, create_all применяет её к движку.
    """
    Base.metadata.create_all(bind=engine)


# ---------- CRUD-операции ----------

def upsert_products(rows: list[dict]) -> int:
    """
    Сохраняем/обновляем записи по первичному ключу (id).
    Стратегия простая и понятная: «найти по PK → обновить поля → если нет — создать».
    Возвращает кол-во затронутых строк.
    """
    if not rows:
        return 0

    now = datetime.now(timezone.utc)
    # Открываем сессию как контекстный менеджер — коммит/роллбек произойдут корректно.
    with SessionLocal() as session:  # type: Session
        affected = 0
        for r in rows:
            pid_val = r.get("pid")
            if not pid_val:
                continue

            # 1) Пытаемся найти объект по первичному ключу (быстро и прозрачно).
            obj: Product | None = session.query(
                Product).filter_by(pid=pid_val).first()

            if obj is None:
                # 2а) Нет в БД — создаём новый объект и добавляем в сессию.
                obj = Product(pid=pid_val)
                session.add(obj)

            # 3) В любом случае (новый или существующий) — обновляем поля.

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

        # 4) Фиксируем изменения одним коммитом.
        session.commit()

        return affected
