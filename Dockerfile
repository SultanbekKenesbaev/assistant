FROM python:3.11-slim

# Ставим только то, что реально нужно
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# зависимости
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# код и статик
COPY . ./

# окружение по умолчанию
ENV OUTPUT_DIR=/app/storage/outputs
ENV FRONTEND_DIR=/app/frontend
ENV CHROMA_DIR=/app/storage/chroma
ENV DOCS_DIR=/app/data/docs
ENV PYTHONUNBUFFERED=1

# Render пробрасывает порт через $PORT — используем его
EXPOSE 8000
CMD ["bash", "-lc", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
