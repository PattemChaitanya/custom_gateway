# Stage 1 – install dependencies
FROM python:3.13-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential libpq-dev curl \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --target=/app/packages -r requirements.txt

# Stage 2 – runtime image
FROM python:3.13-slim AS runtime

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
  libpq-dev curl \
  && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/packages /usr/local/lib/python3.13/site-packages/
COPY . .

ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1

EXPOSE 8000

# Run migrations then start the server
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1"]
