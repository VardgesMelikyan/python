from fastapi import FastAPI

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
