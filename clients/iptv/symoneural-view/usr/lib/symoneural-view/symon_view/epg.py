"""EPG (Electronic Program Guide) management.

Consolidates the former ``epg_utils`` and ``multiepg`` modules into a
single, thread-safe EPG subsystem.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta
from typing import Any

from PyQt6.QtWidgets import (
    QDialog,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

logger = logging.getLogger(__name__)


class EPGManager:
    """Manage EPG data with thread-safe lookups."""

    def __init__(self) -> None:
        self.epg_data: dict[str, list[dict[str, Any]]] = {}
        self.epg_index: dict[str, dict[str, Any]] = {}
        self.last_update: datetime | None = None
        self.lock = threading.RLock()

    def update_epg(self, epg_data: dict[str, list[dict[str, Any]]]) -> None:
        """Replace EPG data and rebuild index."""
        with self.lock:
            self.epg_data = epg_data
            self.last_update = datetime.now()
            self._build_index()
            logger.info("EPG updated: %d channels", len(epg_data))

    def _build_index(self) -> None:
        self.epg_index = {}
        for channel_id, programmes in self.epg_data.items():
            self.epg_index[channel_id] = {}
            for prog in programmes:
                start = prog.get("start", "")
                if start:
                    self.epg_index[channel_id][start] = prog

    def get_current_program(self, channel_id: str) -> dict[str, Any] | None:
        """Return the programme currently airing on *channel_id*."""
        with self.lock:
            if channel_id not in self.epg_data:
                return None

            programmes = self.epg_data[channel_id]
            now = datetime.now()

            for prog in programmes:
                try:
                    start = datetime.fromisoformat(prog.get("start", ""))
                    stop = datetime.fromisoformat(prog.get("stop", ""))
                    if start <= now <= stop:
                        return prog
                except (ValueError, TypeError):
                    continue

            return programmes[0] if programmes else None

    def get_upcoming_programs(
        self, channel_id: str, hours: int = 24,
    ) -> list[dict[str, Any]]:
        """Return upcoming programmes within *hours*."""
        with self.lock:
            if channel_id not in self.epg_data:
                return []

            programmes = self.epg_data[channel_id]
            now = datetime.now()
            future = now + timedelta(hours=hours)

            upcoming: list[dict[str, Any]] = []
            for prog in programmes:
                try:
                    start = datetime.fromisoformat(prog.get("start", ""))
                    if now <= start <= future:
                        upcoming.append(prog)
                except (ValueError, TypeError):
                    continue
            return upcoming

    def search_programs(
        self, query: str, max_results: int = 50,
    ) -> list[dict[str, Any]]:
        """Search programmes by title substring."""
        with self.lock:
            q = query.lower()
            results: list[dict[str, Any]] = []

            for channel_id, programmes in self.epg_data.items():
                for prog in programmes:
                    if q in prog.get("title", "").lower():
                        results.append({"channel": channel_id, "program": prog})
                        if len(results) >= max_results:
                            return results
            return results

    def get_stats(self) -> dict[str, Any]:
        """Return EPG statistics."""
        with self.lock:
            total = sum(len(p) for p in self.epg_data.values())
            return {
                "channels": len(self.epg_data),
                "total_programs": total,
                "last_update": self.last_update.isoformat() if self.last_update else None,
                "age_minutes": (
                    (datetime.now() - self.last_update).total_seconds() / 60
                    if self.last_update
                    else None
                ),
            }


class MultiEPG(QDialog):
    """Multi-channel EPG grid dialog."""

    def __init__(
        self,
        data_map: dict[str, list[dict[str, Any]]],
        epg_index: dict[str, dict[str, Any]],
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Multi EPG")
        layout = QVBoxLayout(self)
        table = QTableWidget()
        rows = sum(len(v) for v in data_map.values())
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Channel", "Now", "Next"])
        table.setRowCount(rows)
        r = 0
        for items in data_map.values():
            for ch in items:
                key = ch.get("stream_id") or ch.get("tvg_id")
                if key:
                    progs = epg_index.get(key, {}).get("programs", [])
                else:
                    progs = []
                nowp = progs[0].get("title", "-") if progs else "-"
                nextp = progs[1].get("title", "-") if len(progs) > 1 else "-"
                table.setItem(r, 0, QTableWidgetItem(ch.get("name", "")))
                table.setItem(r, 1, QTableWidgetItem(nowp))
                table.setItem(r, 2, QTableWidgetItem(nextp))
                r += 1
        layout.addWidget(table)
