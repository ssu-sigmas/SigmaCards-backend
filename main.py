from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
import httpx

# Загрузить переменные окружения
load_dotenv()

# Создать FastAPI приложение
app = FastAPI(
    title="SigmaCards API",
    description="AI-powered SRS learning application",
    version="0.1.0",
    docs_url="/docs",
    openapi_url="/openapi.json"
)

# ==========================================
# MIDDLEWARE
# ==========================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# ML SERVICE CLIENT
# ==========================================

ML_SERVICE_URL = os.getenv("ML_SERVICE_URL", "http://localhost:8001")
ML_SERVICE_TIMEOUT = int(os.getenv("ML_SERVICE_TIMEOUT", "60"))

async def call_ml_service(endpoint: str, data: dict):
    """Вызвать ML микросервис"""
    url = f"{ML_SERVICE_URL}{endpoint}"
    try:
        async with httpx.AsyncClient(timeout=ML_SERVICE_TIMEOUT) as client:
            response = await client.post(url, json=data)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        return {"error": str(e), "status": "ml_service_error"}

# ==========================================
# ROUTES
# ==========================================

@app.get("/")
async def root():
    """Главная страница"""
    return {
        "message": "Welcome to SigmaCards API",
        "version": "0.1.0",
        "docs_url": "/docs"
    }

@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {
        "status": "ok",
        "service": "sigmacards-api",
        "environment": os.getenv("ENV", "unknown"),
        "ml_service": ML_SERVICE_URL
    }

@app.post("/api/upload-image")
async def upload_image(file: bytes, deck_id: str):
    """
    Загрузить изображение для OCR.
    Отправляет на ML микросервис, который вернет текст и сгенерирует карточки.
    """
    # Отправить на ML сервис
    result = await call_ml_service(
        "/process-image",
        {
            "image": file.hex(),  # Конвертируем в hex для JSON
            "deck_id": deck_id
        }
    )
    return result

# ==========================================
# TODO: Добавить роуты
# ==========================================
# - /auth/* - авторизация (login, register, refresh)
# - /decks/* - колоды (create, get, delete, update)
# - /cards/* - карточки (create, get, delete, update)
# - /review/* - обучение (submit review, get due cards)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        env_file=".env"
    )
