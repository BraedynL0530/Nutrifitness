FROM python:3.11-slim
LABEL authors="Owner"
WORKDIR /app

RUN apt-get update && apt-get install -y \
    postgresql-client \
    libzbar0 \
    libgl1 \
    libglib2.0-0 \
    libzbar-dev \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Skip WSGI check for now
EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate && python manage.py collectstatic --noinput && gunicorn --bind 0.0.0.0:8000 --workers 1 --timeout 120 --log-level debug Nutrifitness.wsgi:application"]
