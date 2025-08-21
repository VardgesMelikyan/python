from fastapi import FastAPI, BackgroundTasks, HTTPException
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
