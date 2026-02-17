import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, make_msgid
from functools import lru_cache
from typing import Annotated, Any

from bs4 import BeautifulSoup
from core.config import (
    BACKEND_BASEURL,
    DEBUG,
    EMAIL_PRESIGN_SECRET,
    JINJA_ENV,
    SMTP_FROM_EMAIL,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_SERVER,
    SMTP_SSL,
    SMTP_TLS,
    SMTP_USER,
)
from core.logger import get_logger
from fastapi import Depends, HTTPException
from itsdangerous import URLSafeTimedSerializer
from jinja2 import (
    TemplateNotFound,
)
from util.api_router import APIRouter

mail_logger = get_logger("mails")


class EmailManager:
    """Utility class for sending emails."""

    def __init__(self) -> None:
        """Initialize the EmailManager, validate SMTP configuration."""
        required = {
            "SMTP_SERVER": SMTP_SERVER,
            "SMTP_PORT": SMTP_PORT,
            "SMTP_USER": SMTP_USER,
            "SMTP_PASSWORD": SMTP_PASSWORD,
            "SMTP_FROM_EMAIL": SMTP_FROM_EMAIL,
        }
        missing = [k for k, v in required.items() if not v]
        if missing and not DEBUG:
            raise RuntimeError(
                "Missing SMTP configuration: "
                + ", ".join(missing)
            )
        if SMTP_FROM_EMAIL and "@" not in SMTP_FROM_EMAIL:
            raise RuntimeError(
                f"Invalid SMTP_FROM_EMAIL:"
                f" '{SMTP_FROM_EMAIL}' is missing '@'"
            )

        self._smtp_available = False
        mail_logger.info(
            "SMTP client configured (server: %s, port: %s)",
            SMTP_SERVER,
            SMTP_PORT,
        )

    def _smtp_connection(
        self, timeout: int = 10
    ) -> smtplib.SMTP:
        """Return the appropriate SMTP connection.

        Uses SMTP_SSL (implicit TLS, typically port 465) when
        SMTP_SSL is set, otherwise plain SMTP (with optional
        STARTTLS upgrade via SMTP_TLS, typically port 587).
        """
        if SMTP_SSL:
            return smtplib.SMTP_SSL(
                SMTP_SERVER, SMTP_PORT, timeout=timeout
            )
        return smtplib.SMTP(
            SMTP_SERVER, SMTP_PORT, timeout=timeout
        )

    def verify_connection(self) -> bool:
        """Verify SMTP connection at startup.

        Returns True if the connection succeeds. On network-level
        failures (timeouts, unreachable hosts) logs a warning and
        returns False so the application can still boot.  Auth
        errors are re-raised because they indicate a real config
        problem.
        """
        try:
            mail_logger.debug(
                "Attempting SMTP connection: server=%s,"
                " port=%s, tls=%s, ssl=%s, user=%s",
                SMTP_SERVER,
                SMTP_PORT,
                SMTP_TLS,
                SMTP_SSL,
                SMTP_USER,
            )
            with self._smtp_connection() as server:
                if SMTP_TLS and not SMTP_SSL:
                    server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
            mail_logger.info(
                "SMTP connection verified successfully"
            )
            self._smtp_available = True
            return True
        except smtplib.SMTPAuthenticationError as e:
            raise RuntimeError(
                "SMTP authentication failed for user"
                f" '{SMTP_USER}': {e}"
            ) from e
        except Exception as e:
            mail_logger.warning(
                "SMTP connection failed: %s. Email sending"
                " will be unavailable — email content will"
                " be logged on send attempts.",
                e,
            )
            self._smtp_available = False
            return False

    def generate_verification_link(self, email: str, router: APIRouter, *, salt: str, confirm_route: str) -> str:
            """Generate a signed verification link."""
            serializer = URLSafeTimedSerializer(EMAIL_PRESIGN_SECRET)
            token = serializer.dumps(email, salt=salt)
            return f"{BACKEND_BASEURL}/api{router.url_path_for(confirm_route, token=token)}"
        
    def send_email(self, target_email: str, subject: str, template: str, template_vars: dict[str, Any]) -> None:
        """Send an email with templated HTML and plain text bodies."""
        # Render HTML email body
        try:
            html_body = JINJA_ENV.get_template(template).render(**template_vars)
        except TemplateNotFound as e:
            mail_logger.error("Email template '%s' not found. Ensure templates directory exists and contains the template.", template)
            raise HTTPException(status_code=500, detail=f"Email template '{template}' not found") from e

        # Render plain text email body
        # Try to load .txt version, fall back to stripping HTML if not found
        text_template_name = template.replace('.jinja', '.txt').replace('.html', '.txt')
        try:
            plain_text_body = JINJA_ENV.get_template(text_template_name).render(**template_vars)
        except TemplateNotFound:
            mail_logger.warning("Plain text template '%s' not found, falling back to HTML stripping", text_template_name)
            soup: BeautifulSoup = BeautifulSoup(html_body, "html.parser")
            plain_text_body = soup.get_text()

        # Build email
        msg: MIMEMultipart = MIMEMultipart("alternative")
        msg["From"] = formataddr(("text.ur", SMTP_FROM_EMAIL))
        msg["To"] = target_email
        msg["Subject"] = subject
        msg["Reply-To"] = SMTP_FROM_EMAIL
        msg["Message-ID"] = make_msgid(domain=SMTP_FROM_EMAIL.split("@")[1])
        msg["X-Mailer"] = "text.ur"
        msg["X-Auto-Response-Suppress"] = "OOF, DR, RN, NRN, AutoReply"

        mail_logger.info(f"\n[To: {target_email}]\n[Subject: {subject}]\n[Template: {template}]\n[Vars: {template_vars}]")

        msg.attach(MIMEText(plain_text_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        # Send email
        try:
            with self._smtp_connection() as server:
                if SMTP_TLS and not SMTP_SSL:
                    server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)
                mail_logger.info(
                    "Email sent to %s (subject: %s)",
                    target_email,
                    subject,
                )
        except Exception as e:
            mail_logger.error(
                "Failed to send email to %s: %s",
                target_email,
                e,
            )
            mail_logger.warning(
                "Email delivery failed. Content logged"
                " below for manual recovery.\n"
                "[To: %s]\n[Subject: %s]\n"
                "[Body]\n%s",
                target_email,
                subject,
                plain_text_body,
            )
            raise HTTPException(
                status_code=500,
                detail="Failed to send email",
            ) from e


@lru_cache(maxsize=1)
def get_mail_manager() -> EmailManager:
    """Lazily create the EmailManager to avoid import-time side effects."""
    return EmailManager()


Mail = Annotated[EmailManager, Depends(get_mail_manager)]


 
