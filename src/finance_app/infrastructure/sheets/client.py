"""Thin gateway over the Google Sheets v4 API (google-api-python-client)."""

from __future__ import annotations

import logging
import random
import threading
import time
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from typing import Any

from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

SCOPES = ("https://www.googleapis.com/auth/spreadsheets",)
_RETRYABLE = {429, 500, 502, 503, 504}

Row = list[Any]


class SheetsError(RuntimeError):
    """Raised when the Google Sheets API fails permanently."""


class SheetsGateway:
    def __init__(
        self,
        service: Any,
        spreadsheet_id: str,
        max_retries: int = 5,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._service = service
        self._spreadsheet_id = spreadsheet_id
        self._max_retries = max_retries
        self._sleep = sleep
        # googleapiclient/httplib2 share one connection that is not thread-safe:
        # concurrent executes can corrupt the TLS stream, so serialize them.
        self._transport_lock = threading.Lock()

    @classmethod
    def from_service_account_file(
        cls, credentials_path: Path, spreadsheet_id: str
    ) -> SheetsGateway:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        if not credentials_path.is_file():
            raise SheetsError(f"Service account file not found: {credentials_path}")
        credentials = service_account.Credentials.from_service_account_file(
            str(credentials_path), scopes=list(SCOPES)
        )
        service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
        return cls(service, spreadsheet_id)

    def _execute(self, request: Any) -> Any:
        for attempt in range(self._max_retries + 1):
            try:
                with self._transport_lock:
                    return request.execute()
            except HttpError as exc:
                status = int(getattr(exc.resp, "status", 0))
                if status in _RETRYABLE and attempt < self._max_retries:
                    delay = min(2**attempt, 32) + random.random()
                    logger.warning("Sheets API %s, retrying in %.1fs", status, delay)
                    self._sleep(delay)
                    continue
                raise SheetsError(f"Google Sheets API error ({status}): {exc}") from exc
            except OSError as exc:  # transient TLS/socket failures
                if attempt < self._max_retries:
                    delay = min(2**attempt, 32) + random.random()
                    logger.warning("Sheets transport error %r, retrying in %.1fs", exc, delay)
                    self._sleep(delay)
                    continue
                raise SheetsError(f"Google Sheets transport error: {exc}") from exc
        raise SheetsError("Google Sheets API: retries exhausted")  # pragma: no cover

    @property
    def _sheets(self) -> Any:
        return self._service.spreadsheets()

    def sheet_ids(self) -> dict[str, int]:
        meta = self._execute(
            self._sheets.get(
                spreadsheetId=self._spreadsheet_id, fields="sheets.properties(sheetId,title)"
            )
        )
        return {
            s["properties"]["title"]: s["properties"]["sheetId"] for s in meta.get("sheets", [])
        }

    def batch_update(self, requests: Sequence[dict[str, Any]]) -> None:
        if requests:
            self._execute(
                self._sheets.batchUpdate(
                    spreadsheetId=self._spreadsheet_id, body={"requests": list(requests)}
                )
            )

    def add_sheets(self, titles: Iterable[str]) -> None:
        self.batch_update([{"addSheet": {"properties": {"title": t}}} for t in titles])

    def batch_get(self, ranges: Sequence[str]) -> list[list[Row]]:
        response = self._execute(
            self._sheets.values().batchGet(
                spreadsheetId=self._spreadsheet_id,
                ranges=list(ranges),
                valueRenderOption="UNFORMATTED_VALUE",
            )
        )
        return [vr.get("values", []) for vr in response.get("valueRanges", [])]

    def update_values(self, data: Sequence[tuple[str, list[Row]]]) -> None:
        if data:
            self._execute(
                self._sheets.values().batchUpdate(
                    spreadsheetId=self._spreadsheet_id,
                    body={
                        "valueInputOption": "RAW",
                        "data": [{"range": r, "values": v} for r, v in data],
                    },
                )
            )

    def append_values(self, range_: str, rows: list[Row]) -> None:
        if rows:
            self._execute(
                self._sheets.values().append(
                    spreadsheetId=self._spreadsheet_id,
                    range=range_,
                    valueInputOption="RAW",
                    insertDataOption="INSERT_ROWS",
                    body={"values": rows},
                )
            )

    def delete_rows(self, rows: Iterable[tuple[int, int]]) -> None:
        """Delete rows given as (sheet_id, 1-based row number). Done bottom-up in one call."""
        ordered = sorted(set(rows), key=lambda r: (r[0], -r[1]))
        self.batch_update(
            [
                {
                    "deleteDimension": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "ROWS",
                            "startIndex": row - 1,
                            "endIndex": row,
                        }
                    }
                }
                for sheet_id, row in ordered
            ]
        )
