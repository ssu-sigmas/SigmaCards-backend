from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx

from src.core.config import settings
from src.api import auth, users, decks, cards, review

API_V1_PREFIX = "/api/v1"

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


async def call_ml_service(endpoint: str, data: dict):
    """Вызвать ML микросервис"""
    url = f"{settings.ML_SERVICE_URL}{endpoint}"
    try:
        async with httpx.AsyncClient(timeout=settings.ML_SERVICE_TIMEOUT) as client:
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
        "environment": settings.ENV,
        "ml_service": settings.ML_SERVICE_URL
    }


# ==========================================
# API ROUTERS
# ==========================================

app.include_router(auth.router, prefix=API_V1_PREFIX)
app.include_router(users.router, prefix=API_V1_PREFIX)
app.include_router(decks.router, prefix=API_V1_PREFIX)
app.include_router(cards.router, prefix=API_V1_PREFIX)
app.include_router(review.router, prefix=API_V1_PREFIX)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True
    )
