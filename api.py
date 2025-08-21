from fastapi import FastAPI, BackgroundTasks, HTTPException
from sqlalchemy.engine import make_url
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


@app.get("/debug/db")
def debug_db():
    u = make_url("DATABASE_URL")
    return {
        "driver": u.drivername,       # должно быть postgresql+psycopg
        "host": u.host,               # *.supabase.co
        "port": u.port,               # 5432 или 6543 (pooler)
        "database": u.database,       # postgres (по умолчанию)
        "sslmode": u.query.get("sslmode")
    }
