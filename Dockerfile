# Use official Python runtime with fewer vulnerabilities
FROM python:3.11-bookworm

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create all necessary directories with proper permissions AS ROOT
RUN mkdir -p /app/staticfiles /app/mediafiles /app/logs && \
    chmod 755 /app/staticfiles /app/mediafiles /app/logs && \
    touch /app/logs/debug.log && \
    chmod 644 /app/logs/debug.log

# Create non-root user
RUN useradd -m -u 1000 django

# Change ownership of directories to django user
RUN chown -R django:django /app/staticfiles /app/mediafiles /app/logs

# Copy requirements first for better caching
COPY --chown=django:django requirements.txt .

# Install Python dependencies as non-root
USER django
RUN pip install --user --no-cache-dir -r requirements.txt

# Add user Python packages to PATH
ENV PATH="/home/django/.local/bin:${PATH}"

# Copy application code
COPY --chown=django:django . .

# Collect static files
RUN python3 manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://127.0.0.1:8000/health/ || exit 1

# Run application with gunicorn
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120", "--access-logfile", "-"]
