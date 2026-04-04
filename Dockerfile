# Production Dockerfile
FROM python:3.12-slim as builder

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Set working directory
WORKDIR /app

# Installing system dependencies for building packages
RUN apt-get update && apt-get install -y \
    postgresql-client \
	gdal-bin \
	libgdal-dev \
    libpq-dev \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Installing dependencies for Production
COPY requirements/production.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r production.txt


# Production stage
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Installing only necessary runtime dependencies (PostGIS/GDAL)
RUN apt-get update && apt-get install -y \
    postgresql-client \
    gdal-bin \
    libgdal-dev \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copying installed packages from the builder stage
COPY --from=builder /install /usr/local

# Copying project code
COPY . .

# Static file collection
RUN python manage.py collectstatic --noinput

# Creating a non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/api/v1/health/')"

# Launch command
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]