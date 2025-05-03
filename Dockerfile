# /Dockerfile (Исправленная версия)

FROM python:3.10-slim

# Устанавливаем рабочую директорию и добавляем ее в PYTHONPATH
ENV PYTHONPATH=/app
WORKDIR /app

# Устанавливаем системные зависимости:
# - gcc, libpq-dev: для сборки некоторых Python пакетов (например, psycopg2)
# - postgresql-client: для утилит вроде pg_isready (нужно для скрипта ожидания БД в migrate)
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      gcc \
      libpq-dev \
      postgresql-client \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Копируем только requirements.txt для кэширования зависимостей
COPY requirements.txt .

# Устанавливаем Python зависимости
# Используем --no-cache-dir для уменьшения размера образа
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальной код приложения
COPY . .

# Команда по умолчанию для запуска веб-сервера (используется сервисом 'web')
# Сервисы 'migrate', 'celery', 'celery-beat' переопределяют эту команду в docker-compose.yml
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
