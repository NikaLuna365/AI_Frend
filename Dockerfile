# Dockerfile
FROM python:3.10-slim

# ensure /app is our project root and in PYTHONPATH so "import app" works
ENV PYTHONPATH=/app
WORKDIR /app

# install system dependencies for psycopg2 and build tools
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      gcc \
      libpq-dev \
 && rm -rf /var/lib/apt/lists/*

# copy only requirements first to leverage Docker cache
COPY requirements.txt .

# install Python dependencies (including httpx)
RUN pip install --no-cache-dir -r requirements.txt

# copy the rest of the code
COPY . .

# your production entrypoint
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
