import os
import sys
from importlib import util as importlib_util

from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader, select_autoescape

backend_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
dotenv_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env")
)


if os.path.exists(dotenv_path):
    print(f"Loading environment variables from: {dotenv_path}")
    load_dotenv(dotenv_path)
else:
    print("No .env file found, using system environment variables.")

DEBUG = os.getenv("DEBUG", "False").lower() == "true"
LOG_FILE_DIR = os.getenv("LOG_FILE_DIR", os.path.join(backend_path, "logs"))
ENABLE_LOGGING = os.getenv("ENABLE_LOGGING", "False").lower() == "true"

# DB
PGBOUNCER_PORT: int | None = int(
    os.getenv("PGBOUNCER_PORT")) if os.getenv("PGBOUNCER_PORT") else None
PGBOUNCER_HOST: str | None = os.getenv(
    "PGBOUNCER_HOST") if os.getenv("PGBOUNCER_HOST") else None


POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "dev")
POSTGRES_DB: str = os.getenv("POSTGRES_DB", "prod")
POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", 5433))
DB_CONNECTION_TIMEOUT: int = int(
    os.getenv("DB_CONNECTION_TIMEOUT", 10))  # seconds
DB_STATEMENT_TIMEOUT: int = int(
    os.getenv("DB_STATEMENT_TIMEOUT", 10000))  # milliseconds

IS_TEST_ENV = os.getenv("TESTING", "").lower() == "true"
if IS_TEST_ENV:
    POSTGRES_DB = "test"

user = POSTGRES_USER
password = POSTGRES_PASSWORD
host = PGBOUNCER_HOST or POSTGRES_HOST if not IS_TEST_ENV else POSTGRES_HOST
port = PGBOUNCER_PORT or POSTGRES_PORT if not IS_TEST_ENV else POSTGRES_PORT
db = POSTGRES_DB if not IS_TEST_ENV else "test"

# Async database URL for application (using asyncpg)
DATABASE_URL: str = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"

# Sync database URL for migrations and scripts (using psycopg2)
SYNC_DATABASE_URL: str = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"

# REDIS
REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD")
REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")

# S3
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_ENDPOINT_PORT = os.getenv("AWS_ENDPOINT_PORT")
AWS_ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL") + \
    f":{AWS_ENDPOINT_PORT}" if AWS_ENDPOINT_PORT else ""
AWS_REGION = os.getenv("AWS_REGION")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
S3_BUCKET = os.getenv("S3_BUCKET", "default")

if IS_TEST_ENV:
    S3_BUCKET = S3_BUCKET + "-test"

JWT_ACCESS_EXPIRATION_MINUTES = float(
    os.getenv("JWT_ACCESS_EXPIRATION_MINUTES", 30))
JWT_REFRESH_EXPIRATION_DAYS = float(os.getenv("JWT_REFRESH_EXPIRATION_DAYS", 7))
JWT_REFRESH_GUEST_EXPIRATION_DAYS = float(
    os.getenv("JWT_REFRESH_GUEST_EXPIRATION_DAYS", 30))
JWT_SECRET = os.getenv("JWT_SECRET")

# EMAIL
EMAIL_PRESIGN_SECRET = os.getenv("EMAIL_PRESIGN_SECRET")
REGISTER_LINK_EXPIRY_DAYS = float(os.getenv("REGISTER_LINK_EXPIRY_DAYS", 7))
PASSWORD_RESET_LINK_EXPIRY_MINUTES = float(
    os.getenv("RESET_PASSWORD_LINK_EXPIRY_MINUTES", 30)
)
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT")) if os.getenv("SMTP_PORT") else None
# Default to True for most SMTP servers
SMTP_TLS = os.getenv("SMTP_TLS", "True").lower() == "true"
# Sender email address
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL")

# APP
JINJA_ENV = Environment(
    loader=FileSystemLoader(os.path.join(os.getcwd(), "templates")),
    autoescape=select_autoescape(["html"])
)
FRONTEND_BASEURL = os.getenv("ORIGIN")
if not FRONTEND_BASEURL and not IS_TEST_ENV:
    raise RuntimeError(
        "Required environment variable ORIGIN is not set"
    )
BACKEND_BASEURL = os.getenv("PUBLIC_BACKEND_BASEURL", "http://localhost:8000")
# Should be True in production (requires HTTPS)
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "True").lower() == "true"
COOKIE_SAMESITE = os.getenv(
    "COOKIE_SAMESITE", "lax"
)
MAX_UPLOAD_SIZE_MB = int(os.getenv("PUBLIC_MAX_UPLOAD_SIZE_MB", 50))
MAX_COMMENT_LENGTH = int(os.getenv("PUBLIC_MAX_COMMENT_LENGTH", 2000))
MAX_DOCUMENT_NAME_LENGTH = int(os.getenv("PUBLIC_MAX_DOCUMENT_NAME_LENGTH", 255))
MAX_DOCUMENT_DESCRIPTION_LENGTH = int(os.getenv("PUBLIC_MAX_DOCUMENT_DESCRIPTION_LENGTH", 5000))

# TAGS
MAX_TAGS_PER_DOCUMENT = int(os.getenv("PUBLIC_MAX_TAGS_PER_DOCUMENT", 50))
MAX_TAGS_PER_COMMENT = int(os.getenv("PUBLIC_MAX_TAGS_PER_COMMENT", 15))
