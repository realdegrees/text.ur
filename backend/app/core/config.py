import os

from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader, select_autoescape

backend_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
dotenv_path = os.path.join(backend_path, ".env")
load_dotenv(dotenv_path)

DEBUG = os.getenv("DEBUG", "False").lower() == "true"
LOG_FILE_DIR = os.getenv("LOG_FILE_DIR", os.path.join(backend_path, "logs"))
ENABLE_LOGGING = os.getenv("ENABLE_LOGGING", "False").lower() == "true"

# DB
PGBOUNCER_PORT: int | None = int(os.getenv("PGBOUNCER_PORT", None))
PGBOUNCER_ENABLE: bool = os.getenv("PGBOUNCER_ENABLE", "False").lower() == "true"

POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "dev")
POSTGRES_DB: str = os.getenv("POSTGRES_DB", "prod")
POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", 5433))

DATABASE_URL: str = (
    f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{PGBOUNCER_PORT or POSTGRES_PORT}/{POSTGRES_DB}"
)

# REDIS
REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD")
REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")

# S3
S3_PRESIGN_EXPIRY = int(os.getenv("S3_PRESIGN_EXPIRY", 3600))
AWS_ACCESS_KEY= os.getenv("AWS_ACCESS_KEY")
AWS_ENDPOINT_PORT= os.getenv("AWS_ENDPOINT_PORT") 
AWS_ENDPOINT_URL= os.getenv("AWS_ENDPOINT_URL") + f":{AWS_ENDPOINT_PORT}" if AWS_ENDPOINT_PORT else ""
AWS_REGION= os.getenv("AWS_REGION")
AWS_SECRET_KEY= os.getenv("AWS_SECRET_KEY")
S3_BUCKET= os.getenv("S3_BUCKET")

JWT_ACCESS_EXPIRATION_MINUTES = int(
    os.getenv("JWT_ACCESS_EXPIRATION_MINUTES", 30))
JWT_REFRESH_EXPIRATION_DAYS = int(os.getenv("JWT_REFRESH_EXPIRATION_DAYS", 7))
JWT_SECRET = os.getenv("JWT_SECRET")

# EMAIL
EMAIL_PRESIGN_SECRET = os.getenv("EMAIL_PRESIGN_SECRET")
EMAIL_PRESIGN_EXPIRY = int(os.getenv("EMAIL_PRESIGN_EXPIRY", 3600)) # seconds
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT"))
SMTP_TLS = os.getenv("SMTP_TLS", "False").lower() == "true"

# APP
JINJA_ENV = Environment(
    loader=FileSystemLoader(os.path.join(os.getcwd(), "templates")),
    autoescape=select_autoescape(["html"])
)
FRONTEND_BASEURL = os.getenv("FRONTEND_BASEURL")
BACKEND_BASEURL = os.getenv("BACKEND_BASEURL")
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "True").lower() == "true"  # Should be True in production (requires HTTPS)
COOKIE_SAMESITE = os.getenv(
    "COOKIE_SAMESITE", "strict"
)  # 'none' with different frontend/backend origins; 'strict' with same origin (reverse proxy)