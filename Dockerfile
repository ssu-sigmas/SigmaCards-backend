FROM python:3.11-slim

WORKDIR /app

# Установить системные зависимости для PostgreSQL
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Установить Python зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копировать код приложения
COPY . .

# Команда по умолчанию
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
