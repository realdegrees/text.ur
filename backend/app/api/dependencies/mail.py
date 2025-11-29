import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from functools import lru_cache
from typing import Annotated, Any

from bs4 import BeautifulSoup
from core.config import (
    BACKEND_BASEURL,
    DEBUG,
    EMAIL_PRESIGN_SECRET,
    JINJA_ENV,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_SERVER,
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

app_logger = get_logger("app")
mail_logger = get_logger("mails")


class EmailManager:
    """Utility class for sending emails."""

    def __init__(self) -> None:
        """Initialize the EmailManager, check SMTP configuration."""
        # Perform a connection verification automatically during initialization
        if not all([SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD]) and not DEBUG:
            raise RuntimeError("Not all required SMTP configuration variables are set.")
        
        self.verify_connection()

    def verify_connection(self) -> bool:
        """Verify SMTP connection at startup.

        Returns True if successful, False if verification failed but the service
        is disabled or DEBUG is set. Raises an exception when SMTP is enabled and
        the verification fails in non-debug (production) mode.
        """
        try:
            app_logger.debug(
                "Attempting SMTP connection: server=%s, port=%s, tls=%s, user=%s",
                SMTP_SERVER, SMTP_PORT, SMTP_TLS, SMTP_USER
            )
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
                if SMTP_TLS:
                    server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
            app_logger.info("SMTP connection verified successfully")
            return True
        except smtplib.SMTPAuthenticationError as e:
            raise RuntimeError(f"SMTP authentication failed for user '{SMTP_USER}': {e}") from e
        except Exception as e:
            raise RuntimeError(f"Failed to connect to SMTP server: {e}") from e

    def generate_verification_link(self, email: str, router: APIRouter, *, salt: str, confirm_route: str) -> str:
            """Generate a signed verification link."""
            serializer = URLSafeTimedSerializer(EMAIL_PRESIGN_SECRET)
            token = serializer.dumps(email, salt=salt)
            return f"{BACKEND_BASEURL}/api{router.url_path_for(confirm_route, token=token)}"
        
    def send_email(self, target_email: str, subject: str, template: str, template_vars: dict[str, Any]) -> None:
        """Send an email with a templated HTML body."""
        # Render email body
        try:
            html_body = JINJA_ENV.get_template(template).render(**template_vars)
        except TemplateNotFound as e:
            mail_logger.error("Email template '%s' not found. Ensure templates directory exists and contains the template.", template)
            raise HTTPException(status_code=500, detail=f"Email template '{template}' not found") from e

        # Build email
        msg: MIMEMultipart = MIMEMultipart("alternative")
        msg["From"] = SMTP_USER
        msg["To"] = target_email
        msg["Subject"] = subject

        # Generate plain text version by stripping HTML tags

        soup: BeautifulSoup = BeautifulSoup(html_body, "html.parser")
        plain_text_body: str = soup.get_text()
        
        mail_logger.info(f"\n[To: {target_email}]\n[Subject: {subject}]\n[Template: {template}]\n[Vars: {template_vars}]")

        msg.attach(MIMEText(plain_text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        # Send email
        try:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                if SMTP_TLS:
                    server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)
                mail_logger.info("Email sent to %s (subject: %s)", target_email, subject)
        except Exception as e:
            mail_logger.error("Failed to send email to %s: %s", target_email, e, exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to send email") from e


@lru_cache(maxsize=1)
def get_mail_manager() -> EmailManager:
    """Lazily create the EmailManager to avoid import-time side effects."""
    return EmailManager()


Mail = Annotated[EmailManager, Depends(get_mail_manager)]


 
