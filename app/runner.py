from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from .config import AppConfig
from .emailer import EmailSender
from .email_templates import (
    build_daily_summary_html,
    build_daily_summary_text,
    build_regular_email_html,
    build_regular_email_subject,
    build_regular_email_text,
    build_temporary_issue_html,
    build_temporary_issue_subject,
    build_temporary_issue_text,
)
from .emgs_client import EmgsClient
from .models import TemporaryExternalServiceError, TemporaryIssue, UnexpectedResponseError, VisaSnapshot
from .state_store import (
    ensure_daily_state,
    get_now_in_tz,
    load_state,
    save_state,
    should_send_daily_summary,
    should_send_issue_notification,
)


def has_changed(old_snapshot: dict | None, new_snapshot: VisaSnapshot) -> bool:
    if old_snapshot is None:
        return True

    old_fingerprint = {
        "percentage": old_snapshot.get("percentage"),
        "percentage_color": old_snapshot.get("percentage_color"),
        "application_status": old_snapshot.get("application_status"),
        "application_number": old_snapshot.get("application_number"),
        "history_top": (old_snapshot.get("history") or [None])[0],
    }
    return old_fingerprint != new_snapshot.stable_fingerprint()


def run_cycle(config: AppConfig, state_path: Path, logger) -> None:
    state = load_state(state_path)
    now_local = get_now_in_tz(config.timezone)
    current_day = now_local.strftime("%Y-%m-%d")

    email_sender = EmailSender(
        smtp_host=config.smtp_host,
        smtp_port=config.smtp_port,
        smtp_user=config.smtp_user,
        smtp_password=config.smtp_password,
        smtp_use_tls=config.smtp_use_tls,
        logger=logger,
    )

    logger.info("Cycle started")

    for target in config.targets:
        passport_key = target.passport_number
        daily_entry = ensure_daily_state(state, passport_key, current_day)
        issue_state = state.setdefault("_issues", {}).setdefault(
            passport_key,
            {
                "consecutive_failures": 0,
                "last_error": None,
                "last_issue_email_sent_at": None,
            },
        )

        client = EmgsClient(
            timeout=config.request_timeout,
            logger=logger,
            log_request_response=config.log_request_response,
        )

        try:
            snapshot = client.check(target.passport_number, config.nationality)
            display_name = snapshot.full_name or target.passport_number
            old_snapshot = state.get(passport_key)

            changed = has_changed(old_snapshot, snapshot)
            previous_percentage = old_snapshot.get("percentage") if old_snapshot else None
            current_percentage = snapshot.percentage
            percentage_changed = previous_percentage != current_percentage and old_snapshot is not None

            if percentage_changed:
                daily_entry["percentage_changed_today"] = True

            issue_state["consecutive_failures"] = 0
            issue_state["last_error"] = None

            if config.always_email:
                should_send_regular = True
                changed_text = "SKIPPED (always email mode)"
                regular_mode = "ALWAYS"
            else:
                should_send_regular = changed
                changed_text = "YES" if changed else "NO"
                regular_mode = "CHANGED" if changed else "NO CHANGE"

            logger.info(
                "Checked name=%s passport=%s status=%s percentage=%s color=%s changed=%s send_regular=%s",
                display_name,
                target.passport_number,
                snapshot.application_status or "N/A",
                f"{snapshot.percentage}%" if snapshot.percentage is not None else "N/A",
                snapshot.percentage_color_label or "N/A",
                changed_text,
                should_send_regular,
            )

            if should_send_regular:
                subject = build_regular_email_subject(
                    config.email_subject_prefix,
                    display_name,
                    snapshot,
                    regular_mode,
                )
                body_text = build_regular_email_text(display_name, snapshot, changed_text)
                body_html = build_regular_email_html(display_name, snapshot, changed_text)
                email_sender.send(target.destination_email, subject, body_text, body_html)
                logger.info("Regular email sent to %s", target.destination_email)

            if should_send_daily_summary(
                config.daily_summary_enabled,
                config.always_email,
                daily_entry,
                config.daily_summary_hour,
                config.daily_summary_minute,
                now_local,
            ):
                summary_subject = build_regular_email_subject(
                    config.email_subject_prefix,
                    display_name,
                    snapshot,
                    "DAILY SUMMARY",
                )
                summary_text = build_daily_summary_text(display_name, snapshot, current_day)
                summary_html = build_daily_summary_html(display_name, snapshot, current_day)
                email_sender.send(target.destination_email, summary_subject, summary_text, summary_html)
                daily_entry["summary_sent"] = True
                logger.info("Daily summary email sent to %s", target.destination_email)

            state[passport_key] = asdict(snapshot)
            save_state(state_path, state)

        except TemporaryExternalServiceError as exc:
            issue_state["consecutive_failures"] = int(issue_state.get("consecutive_failures", 0)) + 1
            issue_state["last_error"] = str(exc)

            logger.warning(
                "Temporary external service issue for passport=%s failures=%s error=%s",
                target.passport_number,
                issue_state["consecutive_failures"],
                str(exc),
            )

            if config.error_notify_enabled and should_send_issue_notification(
                issue_state=issue_state,
                now_local=now_local,
                threshold=config.error_notify_after_consecutive_failures,
                cooldown_hours=config.error_notify_cooldown_hours,
            ):
                issue = TemporaryIssue(
                    title="EMGS is temporarily unavailable",
                    detail=(
                        "We could not complete the application check because EMGS or one of its backend providers "
                        "appears to be temporarily unavailable. This does not mean your visa status changed or failed."
                    ),
                    technical_detail=str(exc),
                )
                subject = build_temporary_issue_subject(config.email_subject_prefix, target.passport_number)
                body_text = build_temporary_issue_text(target.passport_number, issue)
                body_html = build_temporary_issue_html(target.passport_number, issue)
                email_sender.send(target.destination_email, subject, body_text, body_html)
                issue_state["last_issue_email_sent_at"] = now_local.isoformat()
                logger.info("Temporary issue notification sent to %s", target.destination_email)

            save_state(state_path, state)

        except UnexpectedResponseError as exc:
            issue_state["consecutive_failures"] = int(issue_state.get("consecutive_failures", 0)) + 1
            issue_state["last_error"] = str(exc)
            logger.warning("Unexpected EMGS response for passport=%s error=%s", target.passport_number, str(exc))
            save_state(state_path, state)

        except Exception as exc:
            issue_state["consecutive_failures"] = int(issue_state.get("consecutive_failures", 0)) + 1
            issue_state["last_error"] = str(exc)
            logger.exception("Unhandled error for passport=%s", target.passport_number)
            save_state(state_path, state)

    logger.info("Cycle finished")