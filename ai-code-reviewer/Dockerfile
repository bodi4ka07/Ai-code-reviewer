FROM python:3.11-slim

WORKDIR /app

# Системні залежності для pylint та компіляції
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Встановлення Python залежностей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копіювання коду
COPY . .

EXPOSE 8000
