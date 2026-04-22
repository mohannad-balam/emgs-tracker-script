from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict
from zoneinfo import ZoneInfo


def load_state(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(path: Path, state: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def get_now_in_tz(timezone_name: str) -> datetime:
    return datetime.now(ZoneInfo(timezone_name))


def ensure_daily_state(state: Dict[str, Any], passport_key: str, current_day: str) -> Dict[str, Any]:
    daily = state.setdefault("_daily", {})
    entry = daily.get(passport_key)

    if not entry or entry.get("date") != current_day:
        entry = {
            "date": current_day,
            "percentage_changed_today": False,
            "summary_sent": False,
        }
        daily[passport_key] = entry

    return entry


def should_send_daily_summary(
    daily_summary_enabled: bool,
    always_email: bool,
    daily_entry: Dict[str, Any],
    summary_hour: int,
    summary_minute: int,
    now_local: datetime,
) -> bool:
    if not daily_summary_enabled:
        return False
    if always_email:
        return False
    if daily_entry.get("summary_sent"):
        return False
    if daily_entry.get("percentage_changed_today"):
        return False

    current_minutes = now_local.hour * 60 + now_local.minute
    summary_minutes = summary_hour * 60 + summary_minute
    return current_minutes >= summary_minutes


def should_send_issue_notification(
    issue_state: Dict[str, Any],
    now_local: datetime,
    threshold: int,
    cooldown_hours: int,
) -> bool:
    consecutive_failures = int(issue_state.get("consecutive_failures", 0))
    if consecutive_failures < threshold:
        return False

    last_sent = issue_state.get("last_issue_email_sent_at")
    if not last_sent:
        return True

    try:
        last_sent_dt = datetime.fromisoformat(last_sent)
    except Exception:
        return True

    return now_local >= last_sent_dt + timedelta(hours=cooldown_hours)