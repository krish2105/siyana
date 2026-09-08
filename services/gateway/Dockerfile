# SIYANA API gateway. CPU-only torch keeps the image small enough for Render's free tier.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 libpq5 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN sed -e '/^torch==/d' -e '/^torchvision==/d' requirements.txt > /tmp/req.txt \
 && pip install --extra-index-url https://download.pytorch.org/whl/cpu torch torchvision \
 && pip install -r /tmp/req.txt
COPY services ./services
COPY ingest ./ingest
COPY db ./db
COPY data/metrics ./data/metrics
COPY data/models/rul_lgbm.txt ./data/models/rul_lgbm.txt
EXPOSE 8000
CMD ["sh", "-c", "python db/migrate.py && uvicorn services.gateway.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
