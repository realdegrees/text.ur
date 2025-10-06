import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Annotated, Any

from bs4 import BeautifulSoup
from itsdangerous import URLSafeTimedSerializer
from core.config import (
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
from jinja2 import Environment, FileSystemLoader, select_autoescape

from util.api_router import APIRouter

app_logger = get_logger("app")
mail_logger = get_logger("mails")


class EmailManager:
    """Utility class for sending emails."""
    
    def __init__(self) -> None:
        """Initialize the EmailManager, check SMTP configuration and connectivity."""
        self.enabled: bool = all([SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD])
        if not self.enabled:
            app_logger.warning("⚠️ SMTP is not fully configured. Email sending is disabled. Emails will be printed to the mail logger only.")
                
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            try:
                if SMTP_TLS:
                    server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
            except Exception as e:
                app_logger.error(f"⚠️ Failed to connect to SMTP server: {e}. Email sending is disabled. Emails will be printed to the mail logger only.")
                self.enabled = False
                
        app_logger.info("✅ SMTP is configured and available.")

    def generate_verification_link(self, email: str, base_url: str, router: APIRouter, *, salt: str, confirm_route: str) -> str:
            """Generate a signed verification link."""
            serializer = URLSafeTimedSerializer(EMAIL_PRESIGN_SECRET)
            token = serializer.dumps(email, salt=salt)
            return f"{base_url}api{router.url_path_for(confirm_route, token=token)}"
        
    def send_email(self, target_email: str, subject: str, template: str, template_vars: dict[str, Any]) -> None:
        """Send an email with a templated HTML body."""
        # Render email body
        html_body = JINJA_ENV.get_template(template).render(**template_vars)

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
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            try:
                if SMTP_TLS:
                    server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)
            except Exception as e:
                mail_logger.error(f"Failed to send email to {target_email}: {e!s}")
                raise HTTPException(status_code=500, detail="Failed to send email") from e


manager = EmailManager()
Mail = Annotated[EmailManager, Depends(lambda: manager)]
