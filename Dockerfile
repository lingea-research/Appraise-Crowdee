# Use an official lightweight Python image
FROM python:3.12-slim

# Keep Python from writing .pyc files and buffer output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies needed to install some Python packages
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (cache layer)
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip \
    && pip install -r /app/requirements.txt

# Create a non-root user and application directories
RUN useradd -m -d /home/app -s /bin/bash app || true \
    && mkdir -p /app /data /app/static \
    && chown -R app:app /app /data /app/static

# Copy project files and set ownership to the app user
COPY --chown=app:app . /app

# Switch to non-root user for runtime
USER app

# Ensure the app user's local bin is on PATH (if pip --user used anywhere)
ENV PATH="/home/app/.local/bin:${PATH}"

# Collect static files as a best-effort during build (may be a no-op)
RUN python manage.py collectstatic --noinput || true

# Expose port used by Django dev server
EXPOSE 8000

# Make data and static mountable from the host
VOLUME ["/data", "/app/static"]

# Default command: run migrations and start dev server
# Keep using the simple Django runserver for development; replace with gunicorn in production
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py runserver 0.0.0.0:8000"]

