import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Annotated, Any

from bs4 import BeautifulSoup
from core.config import (
    BACKEND_BASEURL,
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
        self.enabled: bool = all([SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD])
        if not self.enabled:
            app_logger.warning(
                "SMTP is not fully configured. Email sending is disabled. "
                "Emails will be printed to the mail logger only."
            )

    def verify_connection(self) -> None:
        """Verify SMTP connection at startup."""
        if not self.enabled:
            return
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
        except smtplib.SMTPAuthenticationError as e:
            app_logger.error(
                "SMTP authentication failed for user '%s': %s. "
                "If using Gmail, ensure: 1) 2FA is enabled, 2) App password is correct (no spaces), "
                "3) App password was created for 'Mail'",
                SMTP_USER, e
            )
            self.enabled = False
        except Exception as e:
            app_logger.error("Failed to connect to SMTP server: %s", e)
            self.enabled = False
            app_logger.warning(
                "Email sending is disabled due to SMTP connection failure. "
                "Emails will be printed to the mail logger only."
            )

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
        
        if not self.enabled:
            mail_logger.info(f"--- Email to: {target_email} ---\nSubject: {subject}\n\n{plain_text_body}\n--- End of email ---")
            return

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


manager = EmailManager()
Mail = Annotated[EmailManager, Depends(lambda: manager)]
