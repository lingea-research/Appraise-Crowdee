# Quick Docker instructions

1. Prepare a persistent host folder for the DB and (optionally) static files:

```bash
cd /home/berko/github/Appraise-Crowdee
mkdir -p data
# create an empty sqlite file if you want; otherwise the container will create it
touch data/db.sqlite3
mkdir -p static
# Ensure permission so the container can write the sqlite file
chmod 666 data/db.sqlite3 || true
```

2. Build the image (docker-compose will build automatically if you skip this):

```bash
docker build -t appraise:local .
```

3. Run with docker-compose (recommended):

```bash
# This mounts ./data into the container at /data so the app will create /data/db.sqlite3 and it will persist on the host
docker-compose up -d --build
```

4. Check logs and server status:

```bash
docker-compose logs -f web
```

5. Visit the site in your browser:

http://127.0.0.1:8000/

Notes:
- The Dockerfile ensures the container has a /data directory owned by the runtime user. With the compose mount above, the container will create and use /data/db.sqlite3 for the SQLite database.
- If you see SQLite permission errors, ensure the host file is writable by the container (see chmod above) or mount the host directory with suitable permissions.
- For production use, use a production WSGI server (gunicorn) and a production database (Postgres). This setup is intended for local development/testing only.
# Minimal Dockerfile for running the Appraise Django app
# - Uses python:3.12-slim
# - Installs Python deps from requirements.txt
# - Copies source and runs migrations + runserver

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install minimal build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy project
COPY . .

# Collect static files (best-effort during build)
RUN python manage.py collectstatic --noinput || true

# Expose port
EXPOSE 8000

# Declare the DB file and static as mountable (optional)
VOLUME ["/app/db.sqlite3", "/app/static"]

# Default command: run migrations then start development server
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py runserver 0.0.0.0:8000"]
