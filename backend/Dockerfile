FROM python:3.12-slim
WORKDIR /annotation-software  


COPY requirements.txt .

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential postgresql-client && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get purge -y --auto-remove build-essential && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy application code
COPY app ./app
# Copy database migration files
COPY database ./database

# Copy entrypoint
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/docker-entrypoint.sh"]