FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update -y && apt-get install -y \
    build-essential \
    libpq-dev \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

# Copy the entrypoint script
COPY entrypoint.sh /app/entrypoint.sh

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# Set the environment variable
ENV DJANGO_SETTINGS_MODULE=config.settings

# Set the entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# Set the command
CMD ["gunicorn", "landing.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]



