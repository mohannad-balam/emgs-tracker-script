from __future__ import annotations

import logging
import os
import re
import sys
from dataclasses import dataclass
from typing import List

from dotenv import load_dotenv

from .models import ConfigError, PassportTarget


@dataclass
class AppConfig:
    check_interval_minutes: int
    state_file: str
    always_email: bool
    request_timeout: int

    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    smtp_use_tls: bool
    email_subject_prefix: str

    nationality: str
    targets: List[PassportTarget]

    log_level: str
    log_request_response: bool

    daily_summary_enabled: bool
    daily_summary_hour: int
    daily_summary_minute: int
    timezone: str

    error_notify_enabled: bool
    error_notify_after_consecutive_failures: int
    error_notify_cooldown_hours: int


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ConfigError(f"Missing required environment variable: {name}")
    return value.strip()


def split_csv(value: str) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def normalize_passport(passport_number: str) -> str:
    value = passport_number.strip().upper()
    value = re.sub(r"\s+", "", value)
    value = re.sub(r"[^A-Z0-9]", "", value)
    return value


def normalize_smtp_password(password: str) -> str:
    return password.strip().replace(" ", "")


def load_config() -> AppConfig:
    load_dotenv()

    passports = split_csv(require_env("PASSPORTS"))
    emails = split_csv(require_env("EMAILS"))

    if len(passports) != len(emails):
        raise ConfigError(
            f"PASSPORTS count ({len(passports)}) does not match EMAILS count ({len(emails)})."
        )

    if not passports:
        raise ConfigError("PASSPORTS is empty.")

    targets = [
        PassportTarget(
            passport_number=normalize_passport(passport),
            destination_email=email,
        )
        for passport, email in zip(passports, emails)
    ]

    return AppConfig(
        check_interval_minutes=int(os.getenv("CHECK_INTERVAL_MINUTES", "30")),
        state_file=os.getenv("STATE_FILE", "data/visa_tracker_state.json"),
        always_email=env_bool("ALWAYS_EMAIL", False),
        request_timeout=int(os.getenv("REQUEST_TIMEOUT", "30")),
        smtp_host=require_env("SMTP_HOST"),
        smtp_port=int(require_env("SMTP_PORT")),
        smtp_user=require_env("SMTP_USER"),
        smtp_password=normalize_smtp_password(require_env("SMTP_PASSWORD")),
        smtp_use_tls=env_bool("SMTP_USE_TLS", True),
        email_subject_prefix=os.getenv("EMAIL_SUBJECT_PREFIX", "EMGS Tracker").strip() or "EMGS Tracker",
        nationality=os.getenv("NATIONALITY", "LY").strip() or "LY",
        targets=targets,
        log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper(),
        log_request_response=env_bool("LOG_REQUEST_RESPONSE", True),
        daily_summary_enabled=env_bool("DAILY_SUMMARY_ENABLED", True),
        daily_summary_hour=int(os.getenv("DAILY_SUMMARY_HOUR", "23")),
        daily_summary_minute=int(os.getenv("DAILY_SUMMARY_MINUTE", "55")),
        timezone=os.getenv("TIMEZONE", "Africa/Tripoli").strip() or "Africa/Tripoli",
        error_notify_enabled=env_bool("ERROR_NOTIFY_ENABLED", False),
        error_notify_after_consecutive_failures=int(os.getenv("ERROR_NOTIFY_AFTER_CONSECUTIVE_FAILURES", "3")),
        error_notify_cooldown_hours=int(os.getenv("ERROR_NOTIFY_COOLDOWN_HOURS", "12")),
    )


def setup_logging(level: str) -> logging.Logger:
    logger = logging.getLogger("emgs_tracker")
    logger.setLevel(getattr(logging, level, logging.INFO))
    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger