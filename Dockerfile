# Python 3.11 to match local dev (3.13 had package compatibility issues).
# -slim keeps the image small without going full Alpine (which fights
# psycopg2/scientific wheels).
FROM python:3.11-slim

WORKDIR /app

# Install dependencies first, as their own layer. Docker caches this layer
# and only rebuilds it when requirements.txt changes -- so code edits don't
# trigger a full reinstall on every build.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Then copy the application code.
COPY . .

# Cloud Run provides the port via the $PORT env var (default 8080). Bind to
# 0.0.0.0 so the container accepts external traffic; shell form so $PORT
# expands at runtime.
ENV PORT=8080
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port $PORT"]
