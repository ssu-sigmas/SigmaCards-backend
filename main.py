from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import settings
from src.api import auth, users, decks, cards, review, images, generations

from src.services.ml_service import ml_service
from src.services.kafka_router import kafka_router
from src.grpc.server import CardGenerationGrpcServer
from src.services.storage_service import StorageService

import logging

API_V1_PREFIX = "/api/v1"

logging.basicConfig(level=logging.INFO)

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
    await kafka_router.start()
    await ml_service.startup()
    app.state.grpc_server = CardGenerationGrpcServer(
        host=settings.GRPC_HOST,
        port=settings.GRPC_PORT,
    )
    await app.state.grpc_server.start()
    StorageService.ensure_chunks_lifecycle(settings.S3_TEXT_TTL_DAYS)
    

@app.on_event("shutdown")
async def shutdown_event():
    await kafka_router.stop()
    grpc_server = getattr(app.state, "grpc_server", None)
    if grpc_server:
        await grpc_server.stop()

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
app.include_router(generations.router, prefix=API_V1_PREFIX)

if __name__ == "__main__":
    import asyncio
    from hypercorn.asyncio import serve
    from hypercorn.config import Config

    config = Config()
    config.bind = [f"0.0.0.0:{settings.APP_PORT}"]

    ssl_certfile = settings.SSL_CERTFILE
    ssl_keyfile = settings.SSL_KEYFILE
    if ssl_certfile and ssl_keyfile:
        config.certfile = ssl_certfile
        config.keyfile = ssl_keyfile

    asyncio.run(serve(app, config))
