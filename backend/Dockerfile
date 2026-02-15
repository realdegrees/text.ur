FROM python:3.12-slim
WORKDIR /annotation-software

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install system dependencies and Python packages with cache mount
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends build-essential jq postgresql-client

# Install Python dependencies with pip cache mount
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Clean up build dependencies (keep runtime deps like postgresql-client)
RUN apt-get purge -y --auto-remove build-essential && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy application code
COPY app ./app
# Copy database migration files
COPY database ./database
# Copy gunicorn configuration
COPY gunicorn.conf.py ./gunicorn.conf.py

# Copy entrypoint
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/docker-entrypoint.sh"]