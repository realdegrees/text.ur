# 🚢 Deployment

> [Back to main README](../README.md)

This guide covers both development setup and production deployment of text.ur.

## 📦 Deployment Model

text.ur is currently deployed as a single Docker Compose stack for the University of Regensburg, serving a handful of courses. This all-in-one setup is the recommended starting point and should comfortably scale to thousands of users.

For larger deployments, each service (PostgreSQL, Redis, MinIO, backend, frontend) can be separated and scaled independently based on load.

## Table of Contents

- [📋 Prerequisites](#-prerequisites)
- [🔧 Environment Variables](#-environment-variables)
- [💻 Development Setup](#-development-setup)
- [🏭 Production Deployment](#-production-deployment)
- [🔄 Automatic Migrations](#-automatic-migrations)
- [🌐 Reverse Proxy Configuration](#-reverse-proxy-configuration)
- [♻️ Watchtower Auto-Updates](#️-watchtower-auto-updates)

---

## 📋 Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| Docker + Docker Compose | Latest | Infrastructure services, production deployment |
| Python | 3.12+ | Backend runtime |
| Node.js | 20+ | Frontend runtime |
| pnpm | 10 | Frontend package manager |

---

## 🔧 Environment Variables

Copy `.env.template` to `.env` and configure the values. The tables below list all recognized variables. Values shown are the **code defaults** (what the application uses if the variable is unset). The `.env.template` may override some of these with development-friendly values.

<details>
<summary><strong>PostgreSQL</strong></summary>

| Variable | Code Default | Description |
|---|---|---|
| `POSTGRES_USER` | `postgres` | Database user |
| `POSTGRES_PASSWORD` | `dev` | Database password |
| `POSTGRES_DB` | `prod` | Database name |
| `POSTGRES_HOST` | `localhost` | Database host (use `postgres` in Docker) |
| `POSTGRES_PORT` | `5433` | Database port |
| `PGBOUNCER_HOST` | *(none)* | PgBouncer host - if set, queries are routed through PgBouncer (use `pgbouncer` in Docker) |
| `PGBOUNCER_PORT` | *(none)* | PgBouncer port |
| `DB_STATEMENT_TIMEOUT` | `10000` | SQL statement timeout in milliseconds |
| `DB_CONNECTION_TIMEOUT` | `10` | Connection timeout in seconds |

> PgBouncer is optional. It is used automatically when `PGBOUNCER_HOST` is set.

</details>

<details>
<summary><strong>Redis</strong></summary>

| Variable | Code Default | Description |
|---|---|---|
| `REDIS_HOST` | `localhost` | Redis host (use `redis` in Docker) |
| `REDIS_PORT` | `6379` | Redis port |
| `REDIS_PASSWORD` | *(none)* | Redis password |

> `REDIS_COMMANDER_PORT` (template default: `6016`) is only used by the Docker Compose file for the Redis Commander web UI.

</details>

<details>
<summary><strong>S3 / MinIO</strong></summary>

| Variable | Code Default | Description |
|---|---|---|
| `AWS_ACCESS_KEY` | *(none)* | S3 access key |
| `AWS_SECRET_KEY` | *(none)* | S3 secret key |
| `S3_BUCKET` | `default` | Bucket name for PDF storage |
| `AWS_REGION` | *(none)* | S3 region |
| `AWS_ENDPOINT_URL` | *(none)* | S3 endpoint base URL (use `http://minio` in Docker) |
| `AWS_ENDPOINT_PORT` | *(none)* | S3 endpoint port - appended to `AWS_ENDPOINT_URL` if set |

> `MINIO_CONSOLE_PORT` (template default: `6006`) is only used by the Docker Compose file.

</details>

<details>
<summary><strong>Application</strong></summary>

| Variable | Code Default | Description |
|---|---|---|
| `DEBUG` | `False` | Enable debug mode (disable in production) |
| `DEBUG_ALLOW_REGISTRATION_WITHOUT_EMAIL` | `False` | Allow registration without email verification (for development or environments without SMTP) |
| `ENABLE_LOGGING` | `False` | Enable file-based logging |
| `LOG_FILE_DIR` | `backend/logs` | Directory for log files |
| `ORIGIN` | *(none)* | **Required.** Public frontend URL (used for CORS, email links) |
| `INTERNAL_BACKEND_BASEURL` | `http://localhost:8000` | Backend URL used by SvelteKit server during SSR (use `http://backend:8000` in Docker) |
| `PUBLIC_BACKEND_BASEURL` | `http://localhost:8000` | Backend URL used by the browser for client-side API calls and WebSocket connections |
| `COOKIE_SECURE` | `True` | Require HTTPS for cookies (set `False` for local HTTP development) |
| `COOKIE_SAMESITE` | `lax` | Cookie SameSite attribute |
| `GUEST_ACCOUNT_TTL_DAYS` | `90` | Days before unused guest accounts are eligible for cleanup |

</details>

<details>
<summary><strong>Limits</strong></summary>

| Variable | Code Default | Description |
|---|---|---|
| `PUBLIC_MAX_UPLOAD_SIZE_MB` | `50` | Maximum PDF upload size in MB |
| `PUBLIC_MAX_COMMENT_LENGTH` | `2000` | Maximum comment length in characters |
| `PUBLIC_MAX_DOCUMENT_NAME_LENGTH` | `255` | Maximum document name length |
| `PUBLIC_MAX_DOCUMENT_DESCRIPTION_LENGTH` | `5000` | Maximum document description length |
| `PUBLIC_MAX_TAGS_PER_DOCUMENT` | `50` | Maximum tags per document |
| `PUBLIC_MAX_TAGS_PER_COMMENT` | `15` | Maximum tags per comment |

> Variables prefixed with `PUBLIC_` are embedded in the frontend client bundle and available in the browser.

</details>

<details>
<summary><strong>Email / SMTP</strong></summary>

| Variable | Code Default | Description |
|---|---|---|
| `EMAIL_PRESIGN_SECRET` | *(none)* | Secret for signing email verification URLs |
| `REGISTER_LINK_EXPIRY_DAYS` | `7` | Registration link validity |
| `RESET_PASSWORD_LINK_EXPIRY_MINUTES` | `30` | Password reset link validity |
| `SMTP_USER` | *(none)* | SMTP username |
| `SMTP_FROM_EMAIL` | *(none)* | Sender email address |
| `SMTP_PASSWORD` | *(none)* | SMTP password |
| `SMTP_SERVER` | *(none)* | SMTP server host |
| `SMTP_PORT` | *(none)* | SMTP server port |
| `SMTP_TLS` | `True` | Enable STARTTLS |
| `SMTP_SSL` | `False` | Enable implicit SSL/TLS (port 465) |

> If SMTP is not configured, set `DEBUG_ALLOW_REGISTRATION_WITHOUT_EMAIL=True` to allow registration without email verification.

> `MAILHOG_PORT` (template default: `6026`) is only used by the Docker Compose file for the MailHog web UI.

</details>

<details>
<summary><strong>JWT</strong></summary>

| Variable | Code Default | Description |
|---|---|---|
| `JWT_SECRET` | *(none)* | **Required.** Secret key for signing JWT tokens. Generate with `openssl rand -hex 32` |
| `JWT_ACCESS_EXPIRATION_MINUTES` | `30` | Access token lifetime |
| `JWT_REFRESH_EXPIRATION_DAYS` | `7` | Refresh token lifetime |
| `JWT_REFRESH_GUEST_EXPIRATION_DAYS` | `30` | Refresh token lifetime for guest accounts |

</details>

---

## 💻 Development Setup

Development uses `docker-compose.dev.yml` which runs only the infrastructure services. The backend and frontend run directly on the host for hot-reloading.

### 1. Start Infrastructure

```bash
cp .env.template .env
# Edit .env as needed (defaults work for local development)

docker compose -f docker-compose.dev.yml up -d
```

This starts PostgreSQL, PgBouncer, MinIO, Redis, Redis Commander, and MailHog. See the [Environment Variables](#-environment-variables) section for port configuration.

### 2. Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Apply database migrations
cd database
alembic upgrade head
cd ..

# Start development server with hot-reload
uvicorn app.main:app --reload --port 8000
```

The API documentation is available at `http://localhost:8000/api/docs`.

### 3. Frontend Setup

```bash
cd frontend
pnpm install
pnpm dev
```

The application is available at `http://localhost:5173`.

### 🖥️ VS Code

The repository includes pre-configured **launch configurations** in `.vscode/launch.json` for easy debugging:

| Configuration | Description |
|---|---|
| **Backend** | Launches Uvicorn via `debugpy` - set breakpoints directly in Python code |
| **Frontend** | Launches the SvelteKit dev server with Node.js debugging attached |
| **Frontend: Browser** | Opens Chrome with DevTools source maps pointing at the Svelte source |

Use the VS Code **Run and Debug** panel (Ctrl+Shift+D) to select and launch a configuration. You can run the Backend and Frontend configurations simultaneously for a full debugging experience.

### 💡 Tips

- **MailHog** captures all outgoing emails at `http://localhost:6026` - use this to view registration verification and password reset emails.
- **MinIO Console** is available at `http://localhost:6006` for inspecting uploaded files.
- **Redis Commander** is available at `http://localhost:6016` for inspecting Redis state.
- Set `COOKIE_SECURE=False` in `.env` when developing without HTTPS, otherwise cookies will not be set.
- Set `DEBUG_ALLOW_REGISTRATION_WITHOUT_EMAIL=True` to bypass email verification during development.

---

## 🏭 Production Deployment

Production uses `docker-compose.yml` which runs all services including the backend and frontend as containers.

### 1. Configure Environment

Create `.env` from the template and update for production:

```bash
cp .env.template .env
```

See the [Environment Variables](#-environment-variables) section for descriptions and required variables.

### 2. Start Services

```bash
docker compose up -d
```

This starts all services. The backend container automatically:
1. Waits for PostgreSQL to be ready.
2. Acquires a PostgreSQL advisory lock to prevent concurrent migration runs.
3. Runs Alembic migrations.
4. Releases the lock and starts Gunicorn.

See [Automatic Migrations](#-automatic-migrations) for details.

### 3. Using Pre-Built Images

The `docker-compose.yml` includes commented-out image references. To use pre-built images from the CI pipeline instead of building locally:

```yaml
# Replace the build context with the image reference:
backend:
  image: ghcr.io/realdegrees/text.ur/backend:stable
  # build:
  #   context: ./backend
  #   dockerfile: Dockerfile

frontend:
  image: ghcr.io/realdegrees/text.ur/frontend:stable
  # build:
  #   context: ./frontend
  #   dockerfile: Dockerfile
```

Image tags:
- `stable` - built from the `main` branch
- `latest` - built from the `develop` branch
- `sha-<commit>` - built from a specific commit

### 4. Set Up Reverse Proxy

A reverse proxy is **required** in production for TLS termination. See [Reverse Proxy Configuration](#-reverse-proxy-configuration).

---

## 🔄 Automatic Migrations

When the backend container starts, `docker-entrypoint.sh` handles database migrations automatically:

1. **Wait for PostgreSQL** - polls `pg_isready` until the database is reachable.
2. **Acquire advisory lock** - uses `pg_try_advisory_lock(12345)` to ensure only one container runs migrations at a time. This is critical when scaling to multiple backend replicas.
3. **Run migrations** - if the lock is acquired, runs `alembic upgrade head`. If it fails, the container exits with an error.
4. **Wait for lock release** - if another container already holds the lock, the current container blocks on `pg_advisory_lock(12345)` until the lock is released, then skips migrations and proceeds directly to starting the application.
5. **Release lock** - the lock is released explicitly after successful migration and also on exit via a trap handler.

This means you can safely run multiple backend containers in parallel - only one will execute migrations, and the others will wait and then start serving.

---

## 🌐 Reverse Proxy Configuration

text.ur requires a reverse proxy in production for TLS termination. The proxy should forward traffic to both the frontend and backend:

- **Frontend** (port 3000) - serves pages via SSR and static assets
- **Backend** (port 8000) - serves API requests and WebSocket connections from the browser

The proxy must:
- Terminate TLS (HTTPS)
- Forward `X-Forwarded-For` and `X-Real-IP` headers
- Support WebSocket upgrade for `/api/documents/*/events`

---

## ♻️ Watchtower Auto-Updates

The production `docker-compose.yml` includes a Watchtower instance that monitors containers labeled with `com.centurylinklabs.watchtower.scope=textur`. When a new Docker image is pushed to the registry (e.g. after a CI build), Watchtower automatically pulls the new image and restarts the container.

- **Poll interval**: 30 seconds
- **Scope**: Only containers with the `textur` scope label
- **Cleanup**: Old images are removed after update

To disable auto-updates, remove or stop the `watchtower` service.
