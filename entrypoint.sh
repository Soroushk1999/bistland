#!/bin/bash
set -e

echo "Starting entrypoint script..."

# Function to wait for a service to be ready
wait_for_service() {
    local host=$1
    local port=$2
    local service=$3
    echo "Waiting for $service at $host:$port..."
    local count=0
    while ! nc -z $host $port; do
        sleep 1
        count=$((count + 1))
        if [ $count -gt 60 ]; then
            echo "ERROR: $service did not become available after 60 seconds"
            exit 1
        fi
    done
    echo "$service is ready!"
}

# Wait for services (only wait for what's needed)
if [ -z "$SKIP_WAIT" ]; then
    wait_for_service redis 6379 "Redis"
    
    # Worker needs DB for tasks that access models
    if [[ "$*" == *"celery worker"* ]]; then
        wait_for_service db 5432 "PostgreSQL"
        wait_for_service mongo 27017 "MongoDB"
    fi
    
    # Web service needs all services
    if [[ "$*" == *"gunicorn"* ]]; then
        wait_for_service db 5432 "PostgreSQL"
        wait_for_service mongo 27017 "MongoDB"
        wait_for_service minio 9000 "MinIO"
    fi
    
    echo "All required services are ready!"
fi

# Only run migrations and collectstatic for web service (gunicorn)
if [[ "$*" == *"gunicorn"* ]]; then
    echo "Running migrations..."
    python manage.py migrate --noinput
    
    echo "Collecting static files..."
    python manage.py collectstatic --noinput
    
    echo "Setting up MinIO bucket..."
    python manage.py setup_minio || echo "Warning: MinIO setup failed, continuing..."
    
    # Optionally upload sample media (set UPLOAD_SAMPLE_MEDIA=1 to enable)
    if [ "${UPLOAD_SAMPLE_MEDIA:-0}" = "1" ]; then
        echo "Uploading sample media to MinIO..."
        python manage.py upload_sample_media || echo "Warning: Sample media upload failed, continuing..."
    fi
fi

# Execute the main command
echo "Starting: $@"
exec "$@"

