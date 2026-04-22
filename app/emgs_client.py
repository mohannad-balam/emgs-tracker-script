from __future__ import annotations

import json
import re
from logging import Logger
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from .models import (
    HistoryItem,
    TemporaryExternalServiceError,
    UnexpectedResponseError,
    VisaSnapshot,
)

SEARCH_FORM_URL = "https://visa.educationmalaysia.gov.my/emgs/application/searchForm/"
SEARCH_POST_URL = "https://visa.educationmalaysia.gov.my/emgs/application/searchPost/"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


class EmgsClient:
    def __init__(self, timeout: int, logger: Logger, log_request_response: bool) -> None:
        self.timeout = timeout
        self.logger = logger
        self.log_request_response = log_request_response
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Referer": SEARCH_FORM_URL,
                "Origin": "https://visa.educationmalaysia.gov.my",
            }
        )

    def check(self, passport_number: str, nationality: str) -> VisaSnapshot:
        html_doc = self._submit_search(passport_number, nationality)
        return self._parse_result(html_doc)

    def _fetch_form_key(self, passport_number: str) -> str:
        self.logger.info("Fetching form page for passport=%s", passport_number)
        response = self.session.get(SEARCH_FORM_URL, timeout=self.timeout)
        response.raise_for_status()

        if self.log_request_response:
            self.logger.info(
                "FORM RESPONSE passport=%s status=%s url=%s",
                passport_number,
                response.status_code,
                response.url,
            )

        soup = BeautifulSoup(response.text, "html.parser")
        form_key_input = soup.find("input", {"name": "form_key"})
        if not form_key_input or not form_key_input.get("value"):
            raise TemporaryExternalServiceError("Could not find form_key on EMGS search form page.")

        return form_key_input["value"]

    def _submit_search(self, passport_number: str, nationality: str) -> str:
        try:
            form_key = self._fetch_form_key(passport_number)
            payload = {
                "form_key": form_key,
                "travel_doc_no": passport_number,
                "nationality": nationality,
                "agreement": "1",
            }

            if self.log_request_response:
                self.logger.info(
                    "POST REQUEST passport=%s url=%s payload=%s",
                    passport_number,
                    SEARCH_POST_URL,
                    json.dumps(payload, ensure_ascii=False),
                )

            response = self.session.post(
                SEARCH_POST_URL,
                data=payload,
                timeout=self.timeout,
                allow_redirects=True,
            )
            response.raise_for_status()

            if self.log_request_response:
                self.logger.info(
                    "POST RESPONSE passport=%s status=%s url=%s",
                    passport_number,
                    response.status_code,
                    response.url,
                )

            text = response.text or ""
            lowered = text.lower()

            if "starsapi.scicom.com.my" in lowered and "unable to connect" in lowered:
                raise TemporaryExternalServiceError(
                    "EMGS could not reach one of its backend providers (Scicom)."
                )

            if "unable to connect to ssl://" in lowered or "unable to connect to https://" in lowered:
                raise TemporaryExternalServiceError(
                    "EMGS returned a temporary backend connectivity error."
                )

            return text

        except requests.Timeout as exc:
            raise TemporaryExternalServiceError("Request to EMGS timed out.") from exc
        except requests.ConnectionError as exc:
            raise TemporaryExternalServiceError("Could not connect to EMGS.") from exc
        except requests.HTTPError as exc:
            status_code = getattr(exc.response, "status_code", None)
            if status_code and 500 <= status_code <= 599:
                raise TemporaryExternalServiceError(f"EMGS returned HTTP {status_code}.") from exc
            raise

    def _parse_result(self, html_doc: str) -> VisaSnapshot:
        soup = BeautifulSoup(html_doc, "html.parser")

        title = soup.title.get_text(strip=True) if soup.title else ""
        if "My Application Status" not in title and "Application Status" not in title:
            possible_message = self._extract_messages(soup)

            lowered = (possible_message or "").lower()
            if "unable to connect" in lowered or "starsapi.scicom.com.my" in lowered:
                raise TemporaryExternalServiceError(possible_message or "Temporary EMGS backend issue.")

            raise UnexpectedResponseError(
                f"Unexpected response page. Title={title or 'N/A'}. Message={possible_message or 'none'}"
            )

        snapshot = VisaSnapshot()

        summary_div = soup.find("div", class_="application-summary")
        if summary_div:
            summary = self._parse_summary(summary_div)
            snapshot.full_name = summary.get("Full Name")
            snapshot.travel_document_number = summary.get("Travel Document Number")
            snapshot.application_number = summary.get("Application Number")
            snapshot.application_type = summary.get("Application Type")
            snapshot.application_status = summary.get("Application Status")

        snapshot.percentage = self._parse_percentage_from_explanation_block(soup)
        snapshot.explanation = self._parse_explanation(soup)
        snapshot.history = self._parse_history(soup)

        color_info = self._parse_color_info_and_active_color(soup)
        snapshot.percentage_color = color_info.get("active_color")
        snapshot.percentage_color_label = color_info.get("active_label")
        snapshot.percentage_color_meaning = color_info.get("active_meaning")

        return snapshot

    @staticmethod
    def _extract_messages(soup: BeautifulSoup) -> str:
        messages: List[str] = []
        for selector in [".messages", ".error-msg", ".success-msg", ".notice-msg", ".validation-advice"]:
            for node in soup.select(selector):
                text = node.get_text(" ", strip=True)
                if text:
                    messages.append(text)
        return " | ".join(messages[:5])

    @staticmethod
    def _parse_summary(summary_div: BeautifulSoup) -> Dict[str, str]:
        result: Dict[str, str] = {}
        labels = [
            "Full Name",
            "Travel Document Number",
            "Application Number",
            "Application Type",
            "Application Status",
        ]

        for li in summary_div.find_all("li"):
            text = li.get_text(" ", strip=True)
            m = re.match(r"^(.*?)\s*:\s*(.+)$", text)
            if not m:
                continue
            key = m.group(1).strip()
            value = m.group(2).strip()
            if key in labels:
                result[key] = value

        return result

    @staticmethod
    def _parse_percentage_from_explanation_block(soup: BeautifulSoup) -> Optional[int]:
        accordion = soup.find(id="accordion1")
        if not accordion:
            return None

        for h2 in accordion.find_all("h2"):
            text = h2.get_text(" ", strip=True)
            m = re.search(r"(\d{1,3})\s*%", text)
            if m:
                value = int(m.group(1))
                if 0 <= value <= 100:
                    return value
        return None

    @staticmethod
    def _parse_explanation(soup: BeautifulSoup) -> Optional[str]:
        accordion = soup.find(id="accordion1")
        if not accordion:
            return None

        inner_divs = accordion.find_all("div", recursive=False)
        search_root = inner_divs[1] if len(inner_divs) > 1 else accordion

        paragraph = search_root.find("p")
        if paragraph:
            text = paragraph.get_text("\n", strip=True)
            text = re.sub(r"\n+", "\n", text).strip()
            return text or None

        text = search_root.get_text("\n", strip=True)
        text = re.sub(r"\n+", "\n", text).strip()
        return text or None

    @staticmethod
    def _parse_history(soup: BeautifulSoup) -> List[HistoryItem]:
        history: List[HistoryItem] = []
        table = soup.find("table", id="form-table")
        if not table:
            return history

        tbody = table.find("tbody")
        if not tbody:
            return history

        for tr in tbody.find_all("tr"):
            cells = tr.find_all("td")
            if len(cells) >= 3:
                date = cells[0].get_text(" ", strip=True)
                status = cells[1].get_text(" ", strip=True)
                remark = cells[2].get_text(" ", strip=True)
                if status and remark:
                    history.append(HistoryItem(date=date, status=status, remark=remark))
        return history

    @staticmethod
    def _extract_bg_color(style_value: str) -> Optional[str]:
        if not style_value:
            return None
        m = re.search(r"background-color\s*:\s*(#[0-9a-fA-F]{3,6})", style_value)
        if m:
            return m.group(1).lower()
        m = re.search(r"background\s*:\s*(#[0-9a-fA-F]{3,6})", style_value)
        if m:
            return m.group(1).lower()
        return None

    @classmethod
    def _parse_color_info_and_active_color(cls, soup: BeautifulSoup) -> Dict[str, Optional[str]]:
        active_color: Optional[str] = None
        accordion = soup.find(id="accordion1")
        if accordion:
            first_color_cell = accordion.find(
                "td",
                attrs={"style": re.compile(r"background-color\s*:", re.IGNORECASE)},
            )
            if first_color_cell and first_color_cell.get("style"):
                active_color = cls._extract_bg_color(first_color_cell.get("style", ""))

        color_legend: Dict[str, Dict[str, str]] = {}
        legend_container = soup.find("div", class_="status-exp2")
        if legend_container:
            legend_table = legend_container.find("table")
            if legend_table:
                for row in legend_table.find_all("tr"):
                    cells = row.find_all("td")
                    if len(cells) < 2:
                        continue
                    img = cells[0].find("img")
                    meaning = cells[1].get_text(" ", strip=True)
                    if not img or not meaning:
                        continue
                    src = (img.get("src") or "").lower()
                    if "green" in src:
                        color_legend["#098136"] = {"label": "Green", "meaning": meaning}
                    elif "amber" in src:
                        color_legend["#f6a317"] = {"label": "Amber", "meaning": meaning}
                    elif "red" in src:
                        color_legend["#d32f2f"] = {"label": "Red", "meaning": meaning}

        if active_color:
            if active_color in color_legend:
                return {
                    "active_color": active_color,
                    "active_label": color_legend[active_color]["label"],
                    "active_meaning": color_legend[active_color]["meaning"],
                }

            normalized = active_color.lower()
            if normalized == "#098136":
                return {
                    "active_color": normalized,
                    "active_label": "Green",
                    "active_meaning": color_legend.get(normalized, {}).get(
                        "meaning",
                        "Your application is progressing accordingly.",
                    ),
                }
            if normalized == "#f6a317":
                return {
                    "active_color": normalized,
                    "active_label": "Amber",
                    "active_meaning": color_legend.get(normalized, {}).get(
                        "meaning",
                        "Your application is pending additional documents or correction by your institution.",
                    ),
                }
            if normalized in {"#d32f2f", "#c3002f"}:
                return {
                    "active_color": "#d32f2f",
                    "active_label": "Red",
                    "active_meaning": color_legend.get("#d32f2f", {}).get(
                        "meaning",
                        "Your application has been rejected/expired at the current stage. Please contact your institution for advice.",
                    ),
                }

        return {
            "active_color": "#6b7280",
            "active_label": "Unknown",
            "active_meaning": "Could not determine the current color status from the page.",
        }