from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from logging import Logger


class EmailSender:
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        smtp_use_tls: bool,
        logger: Logger,
    ) -> None:
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.smtp_use_tls = smtp_use_tls
        self.logger = logger

    def send(self, to_email: str, subject: str, body_text: str, body_html: str) -> None:
        msg = EmailMessage()
        msg["From"] = self.smtp_user
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.set_content(body_text)
        msg.add_alternative(body_html, subtype="html")

        self.logger.info("Sending email to %s with subject=%s", to_email, subject)

        if self.smtp_use_tls:
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as server:
                server.starttls(context=context)
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
        else:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=30, context=context) as server:
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)