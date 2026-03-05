from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import settings
from src.api import auth, users, decks, cards, review, images

from src.services.ml_service import ml_service

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
        "environment": settings.ENV
    }

@app.on_event("startup")
async def startup_event():
    await ml_service.startup()

@app.on_event("shutdown")
async def shutdown_event():
    await ml_service.close()

# ==========================================
# API ROUTERS
# ==========================================

app.include_router(auth.router, prefix=API_V1_PREFIX)
app.include_router(users.router, prefix=API_V1_PREFIX)
app.include_router(decks.router, prefix=API_V1_PREFIX)
app.include_router(cards.router, prefix=API_V1_PREFIX)
app.include_router(review.router, prefix=API_V1_PREFIX)
app.include_router(images.router, prefix=API_V1_PREFIX)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True
    )
