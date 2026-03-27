FROM python:3.11-slim

WORKDIR /app

# Установить системные зависимости для PostgreSQL
RUN apt-get update && apt-get install -y \
    cron \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Установить Python зависимости
COPY requirements-torch.txt .
COPY requirements.txt .
RUN pip install -r requirements-torch.txt
RUN pip install --no-cache-dir -r requirements.txt
RUN python -c "import nltk; nltk.download('punkt_tab')"

# Копировать код приложения
COPY . .

# Команда по умолчанию (HTTP/2 через ALPN при наличии TLS-сертификатов)
CMD ["sh", "-c", "hypercorn main:app --bind 0.0.0.0:${APP_PORT:-8000} ${SSL_CERTFILE:+--certfile $SSL_CERTFILE} ${SSL_KEYFILE:+--keyfile $SSL_KEYFILE}"]
