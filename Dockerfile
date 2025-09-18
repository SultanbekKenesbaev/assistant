FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg espeak-ng && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./

ENV OUTPUT_DIR=/app/storage/outputs
ENV FRONTEND_DIR=/app/frontend
ENV CHROMA_DIR=/app/storage/chroma
ENV DOCS_DIR=/app/data/docs

EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000"]
