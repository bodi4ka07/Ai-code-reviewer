FROM python:3.11-slim

WORKDIR /app

# Системні залежності для компіляції
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Semgrep в окремому venv, щоб його залежності не конфліктували із застосунком
RUN python -m venv /opt/semgrep \
    && /opt/semgrep/bin/pip install --no-cache-dir "semgrep>=1.80,<2"
ENV SEMGREP_BIN=/opt/semgrep/bin/semgrep

# Встановлення Python залежностей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копіювання коду
COPY . .

EXPOSE 8000
