from fastapi import FastAPI, BackgroundTasks, HTTPException
from db_sqlalchemy import DATABASE_URL, Base, engine, SessionLocal, Product
from starlette.responses import JSONResponse
from urllib.parse import urlparse, parse_qs
from main import main
import os
app = FastAPI()

# эндпоинт "/" — корень API


@app.get("/")
def root():
    return {"message": "API работает"}

# эндпоинт "/products"


@app.get("/products")
def get_products():
    # временно возвращаем тестовые данные
    return [
        {"id": 1, "name": "Кроссовки", "price": 4999},
        {"id": 2, "name": "Рюкзак", "price": 2999},
    ]


@app.post("/run-scrape")
def run_scrape(background: BackgroundTasks, token: str):
    if token != os.getenv("CRON_TOKEN"):
        raise HTTPException(status_code=403, detail="forbidden")
    background.add_task(main)  # запускаем в фоне и сразу отвечаем
    return {"status": "queued"}


@app.get("/debug/db-env")
def debug_db_env():
    raw = os.getenv("DATABASE_URL", "")
    if not raw:
        return {"error": "DATABASE_URL is not set"}
    p = urlparse(raw)
    qs = parse_qs(p.query)
    return {
        "scheme": p.scheme,               # например postgresql+psycopg
        "host": p.hostname,
        "port": p.port,
        "database": (p.path or "").lstrip("/"),
        "sslmode": (qs.get("sslmode") or [None])[0],
        # ни user, ни password не возвращаем
    }


@app.get("/debug/db-ping")
def debug_db_ping():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"ok": True}
    except Exception as e:
        return JSONResponse({"error": f"{type(e).__name__}: {e}"}, status_code=500)

# --- 1) СОЗДАТЬ ТАБЛИЦЫ В ТЕКУЩЕЙ БД ---


@app.api_route("/init-db", methods=["GET", "POST"])
def init_db(token: str = Query(None)):
    if token != CRON_TOKEN:
        raise HTTPException(status_code=403, detail="forbidden")
    Base.metadata.create_all(bind=engine)
    # покажем, куда именно подключаемся, но без секретов
    u = DATABASE_URL if isinstance(
        DATABASE_URL, URL) else make_url(str(DATABASE_URL))
    return {
        "status": "created",
        "driver": u.drivername,
        "host": u.host,
        "database": u.database,
        "schema": "public",
        "tables": sorted(list(Base.metadata.tables.keys())),
    }

# --- 2) ТЕСТОВАЯ ВСТАВКА ---


@app.api_route("/insert-test", methods=["GET", "POST"])
def insert_test(token: str = Query(None)):
    if token != CRON_TOKEN:
        raise HTTPException(status_code=403, detail="forbidden")

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    # создадим уникальный pid на основе timestamp, чтобы не упираться в unique(pid)
    test_pid = int(now.timestamp())

    with SessionLocal() as s:
        p = Product(pid=test_pid, name="test", brand="test",
                    price=0.0, rating=0.0, feedbacks=0,
                    url="https://example.com", source="init", query="init",
                    parsed_at=now)
        s.add(p)
        s.commit()
    return {"inserted_pid": test_pid}

# --- 3) ПРОВЕРИТЬ КОЛ-ВО ЗАПИСЕЙ ---


@app.get("/products/count")
def products_count():
    with engine.connect() as conn:
        res = conn.execute(text("select count(*) from products"))
        n = res.scalar_one()
    return {"count": n}
