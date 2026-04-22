from __future__ import annotations

import html
from typing import List, Optional

from .models import HistoryItem, TemporaryIssue, VisaSnapshot


def _color_badge_html(label: Optional[str], color: Optional[str], meaning: Optional[str]) -> str:
    return (
        f'<div style="margin:0 0 16px 0;">'
        f'<span style="display:inline-block;background:{html.escape(color or "#888888")};'
        f'color:#ffffff;padding:8px 14px;border-radius:999px;font-size:13px;'
        f'font-weight:bold;line-height:1;">'
        f'{html.escape(label or "Status")}'
        f'</span>'
        f'<div style="margin-top:8px;font-size:14px;color:#333333;line-height:1.5;">'
        f'{html.escape(meaning or "No color meaning available.")}'
        f'</div>'
        f'</div>'
    )


def _info_row_html(label: str, value: Optional[str]) -> str:
    return (
        f'<tr>'
        f'<td style="padding:10px 12px;border:1px solid #e5e7eb;background:#f9fafb;'
        f'font-weight:bold;font-size:14px;color:#111827;width:220px;">{html.escape(label)}</td>'
        f'<td style="padding:10px 12px;border:1px solid #e5e7eb;font-size:14px;color:#111827;">{html.escape(value or "N/A")}</td>'
        f'</tr>'
    )


def _history_rows_html(history: List[HistoryItem]) -> str:
    rows = []
    for item in history[:5]:
        rows.append(
            f'<tr>'
            f'<td style="padding:10px 12px;border:1px solid #e5e7eb;font-size:13px;color:#111827;vertical-align:top;">{html.escape(item.date)}</td>'
            f'<td style="padding:10px 12px;border:1px solid #e5e7eb;font-size:13px;color:#111827;vertical-align:top;">{html.escape(item.status)}</td>'
            f'<td style="padding:10px 12px;border:1px solid #e5e7eb;font-size:13px;color:#111827;vertical-align:top;">{html.escape(item.remark)}</td>'
            f'</tr>'
        )
    return "".join(rows)


def _base_layout(title: str, body: str, banner_color: str = "#111827") -> str:
    return f"""<!DOCTYPE html>
<html>
  <body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,Helvetica,sans-serif;">
    <div style="max-width:760px;margin:0 auto;padding:24px 16px;">
      <div style="background:#ffffff;border:1px solid #e5e7eb;border-radius:14px;overflow:hidden;">
        <div style="background:{banner_color};padding:20px 24px;">
          <div style="font-size:24px;font-weight:bold;color:#ffffff;line-height:1.3;">{html.escape(title)}</div>
        </div>
        <div style="padding:24px;">
          {body}
        </div>
      </div>
    </div>
  </body>
</html>
"""


def build_regular_email_subject(prefix: str, display_name: str, snapshot: VisaSnapshot, mode: str) -> str:
    percent = f"{snapshot.percentage}%" if snapshot.percentage is not None else "N/A"
    status = snapshot.application_status or "Unknown Status"
    color_label = snapshot.percentage_color_label or "Status"
    return f"[{prefix}] [{display_name}] [{mode}] [{color_label}] {status} - {percent}"


def build_regular_email_text(display_name: str, snapshot: VisaSnapshot, changed_text: str) -> str:
    lines = [
        "EMGS Visa Status Check",
        "=" * 28,
        f"Name: {display_name}",
        f"Changed: {changed_text}",
        f"Color Status: {snapshot.percentage_color_label or 'N/A'}",
        f"Color Meaning: {snapshot.percentage_color_meaning or 'N/A'}",
        "",
        f"Full Name: {snapshot.full_name or 'N/A'}",
        f"Passport: {snapshot.travel_document_number or 'N/A'}",
        f"Application Number: {snapshot.application_number or 'N/A'}",
        f"Application Type: {snapshot.application_type or 'N/A'}",
        f"Application Status: {snapshot.application_status or 'N/A'}",
        f"Percentage: {str(snapshot.percentage) + '%' if snapshot.percentage is not None else 'N/A'}",
    ]
    if snapshot.explanation:
        lines.extend(["", "Explanation", "-" * 11, snapshot.explanation])
    if snapshot.history:
        lines.extend(["", "Latest History", "-" * 14])
        for item in snapshot.history[:5]:
            lines.append(f"{item.date} | {item.status}")
            lines.append(f"  {item.remark}")
    return "\n".join(lines)


def build_regular_email_html(display_name: str, snapshot: VisaSnapshot, changed_text: str) -> str:
    explanation_html = ""
    if snapshot.explanation:
        explanation_html = (
            f'<div style="margin-top:20px;">'
            f'<div style="font-size:16px;font-weight:bold;color:#111827;margin:0 0 10px 0;">Explanation</div>'
            f'<div style="padding:14px 16px;background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;'
            f'font-size:14px;color:#374151;line-height:1.6;white-space:pre-line;">'
            f'{html.escape(snapshot.explanation)}'
            f'</div></div>'
        )

    history_html = ""
    if snapshot.history:
        history_html = (
            f'<div style="margin-top:20px;">'
            f'<div style="font-size:16px;font-weight:bold;color:#111827;margin:0 0 10px 0;">Latest History</div>'
            f'<table style="width:100%;border-collapse:collapse;border-spacing:0;">'
            f'<thead><tr>'
            f'<th style="text-align:left;padding:10px 12px;border:1px solid #e5e7eb;background:#f3f4f6;font-size:13px;color:#111827;">Date</th>'
            f'<th style="text-align:left;padding:10px 12px;border:1px solid #e5e7eb;background:#f3f4f6;font-size:13px;color:#111827;">Status</th>'
            f'<th style="text-align:left;padding:10px 12px;border:1px solid #e5e7eb;background:#f3f4f6;font-size:13px;color:#111827;">Remark</th>'
            f'</tr></thead>'
            f'<tbody>{_history_rows_html(snapshot.history)}</tbody>'
            f'</table></div>'
        )

    body = (
        f'<p style="margin:0 0 16px 0;font-size:14px;color:#374151;line-height:1.6;">'
        f'<strong>Name:</strong> {html.escape(display_name)}<br>'
        f'<strong>Changed:</strong> {html.escape(changed_text)}'
        f'</p>'
        f'{_color_badge_html(snapshot.percentage_color_label, snapshot.percentage_color, snapshot.percentage_color_meaning)}'
        f'<div style="font-size:16px;font-weight:bold;color:#111827;margin:0 0 10px 0;">Summary</div>'
        f'<table style="width:100%;border-collapse:collapse;border-spacing:0;">'
        f'{_info_row_html("Full Name", snapshot.full_name)}'
        f'{_info_row_html("Passport", snapshot.travel_document_number)}'
        f'{_info_row_html("Application Number", snapshot.application_number)}'
        f'{_info_row_html("Application Type", snapshot.application_type)}'
        f'{_info_row_html("Application Status", snapshot.application_status)}'
        f'{_info_row_html("Percentage", f"{snapshot.percentage}%" if snapshot.percentage is not None else "N/A")}'
        f'{_info_row_html("Color Status", snapshot.percentage_color_label)}'
        f'</table>'
        f'{explanation_html}'
        f'{history_html}'
    )
    return _base_layout("EMGS Visa Status Check", body)


def build_daily_summary_text(display_name: str, snapshot: VisaSnapshot, date_str: str) -> str:
    lines = [
        "EMGS Daily Summary",
        "=" * 22,
        f"Name: {display_name}",
        f"Date: {date_str}",
        "",
        "The day has ended with no percentage changes for this application.",
        "The application is still being monitored, and we hope to see progress in the coming day.",
        f"Color Status: {snapshot.percentage_color_label or 'N/A'}",
        f"Color Meaning: {snapshot.percentage_color_meaning or 'N/A'}",
        "",
        f"Full Name: {snapshot.full_name or 'N/A'}",
        f"Passport: {snapshot.travel_document_number or 'N/A'}",
        f"Application Number: {snapshot.application_number or 'N/A'}",
        f"Application Type: {snapshot.application_type or 'N/A'}",
        f"Application Status: {snapshot.application_status or 'N/A'}",
        f"Percentage: {str(snapshot.percentage) + '%' if snapshot.percentage is not None else 'N/A'}",
    ]
    return "\n".join(lines)


def build_daily_summary_html(display_name: str, snapshot: VisaSnapshot, date_str: str) -> str:
    body = (
        f'<p style="margin:0 0 16px 0;font-size:14px;color:#374151;line-height:1.6;">'
        f'<strong>Name:</strong> {html.escape(display_name)}<br>'
        f'<strong>Date:</strong> {html.escape(date_str)}'
        f'</p>'
        f'<div style="margin:0 0 16px 0;padding:14px 16px;background:#fff7ed;border:1px solid #fdba74;'
        f'border-radius:10px;font-size:14px;color:#9a3412;line-height:1.6;">'
        f'The day has ended with no percentage changes for this application.<br>'
        f'The application is still being monitored, and we hope to see progress in the coming day.'
        f'</div>'
        f'{_color_badge_html(snapshot.percentage_color_label, snapshot.percentage_color, snapshot.percentage_color_meaning)}'
        f'<table style="width:100%;border-collapse:collapse;border-spacing:0;">'
        f'{_info_row_html("Full Name", snapshot.full_name)}'
        f'{_info_row_html("Passport", snapshot.travel_document_number)}'
        f'{_info_row_html("Application Number", snapshot.application_number)}'
        f'{_info_row_html("Application Type", snapshot.application_type)}'
        f'{_info_row_html("Application Status", snapshot.application_status)}'
        f'{_info_row_html("Percentage", f"{snapshot.percentage}%" if snapshot.percentage is not None else "N/A")}'
        f'{_info_row_html("Color Status", snapshot.percentage_color_label)}'
        f'</table>'
    )
    return _base_layout("EMGS Daily Summary", body)


def build_temporary_issue_subject(prefix: str, passport: str) -> str:
    return f"[{prefix}] [{passport}] Temporary EMGS Issue"


def build_temporary_issue_text(passport: str, issue: TemporaryIssue) -> str:
    lines = [
        "EMGS Temporary Issue",
        "=" * 20,
        f"Passport: {passport}",
        "",
        issue.title,
        "",
        issue.detail,
    ]
    if issue.technical_detail:
        lines.extend(["", f"Technical detail: {issue.technical_detail}"])
    return "\n".join(lines)


def build_temporary_issue_html(passport: str, issue: TemporaryIssue) -> str:
    body = (
        f'<p style="margin:0 0 16px 0;font-size:14px;color:#374151;line-height:1.6;">'
        f'<strong>Passport:</strong> {html.escape(passport)}'
        f'</p>'
        f'<div style="margin:0 0 16px 0;padding:14px 16px;background:#eff6ff;border:1px solid #93c5fd;'
        f'border-radius:10px;font-size:14px;color:#1e3a8a;line-height:1.7;">'
        f'<strong>{html.escape(issue.title)}</strong><br><br>'
        f'{html.escape(issue.detail)}'
        f'</div>'
    )
    if issue.technical_detail:
        body += (
            f'<div style="padding:12px 14px;background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;'
            f'font-size:13px;color:#374151;line-height:1.6;">'
            f'<strong>Technical detail:</strong> {html.escape(issue.technical_detail)}'
            f'</div>'
        )
    return _base_layout("EMGS Temporary Issue", body, banner_color="#1d4ed8")