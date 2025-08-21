from fastapi import FastAPI, BackgroundTasks, HTTPException
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
