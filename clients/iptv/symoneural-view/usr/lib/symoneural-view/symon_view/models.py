"""Data models for SyMoNeuRaL-View."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CatchupInfo:
    """Catchup/timeshift configuration for a channel."""

    enabled: bool = False
    days: int = 0


@dataclass
class Channel:
    """Represents a single media channel or VOD entry."""

    name: str = "Unknown"
    url: str | None = None
    logo: str | None = None
    group: str = "Uncategorized"
    tvg_id: str | None = None
    stream_id: str | int | None = None
    catchup: CatchupInfo | None = None
    _source: str = ""
    _score: int = 0
    _priority: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Channel:
        """Create a Channel from a plain dictionary.

        Args:
            data: Dictionary with channel attributes.

        Returns:
            Channel instance.
        """
        catchup_raw = data.get("catchup")
        catchup = None
        if isinstance(catchup_raw, dict):
            catchup = CatchupInfo(
                enabled=bool(catchup_raw.get("enabled", False)),
                days=int(catchup_raw.get("days", 0)),
            )
        elif isinstance(catchup_raw, CatchupInfo):
            catchup = catchup_raw

        return cls(
            name=data.get("name", "Unknown"),
            url=data.get("url"),
            logo=data.get("logo") or data.get("stream_icon"),
            group=data.get("group", "Uncategorized"),
            tvg_id=data.get("tvg_id") or data.get("epg_channel_id"),
            stream_id=data.get("stream_id") or data.get("series_id"),
            catchup=catchup,
            _source=data.get("_source", ""),
            _score=data.get("_score", 0),
            _priority=data.get("_priority", ""),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dictionary.

        Returns:
            Dictionary representation.
        """
        result: dict[str, Any] = {
            "name": self.name,
            "group": self.group,
        }
        if self.url is not None:
            result["url"] = self.url
        if self.logo is not None:
            result["logo"] = self.logo
        if self.tvg_id is not None:
            result["tvg_id"] = self.tvg_id
        if self.stream_id is not None:
            result["stream_id"] = self.stream_id
        if self.catchup is not None:
            result["catchup"] = {
                "enabled": self.catchup.enabled,
                "days": self.catchup.days,
            }
        if self._source:
            result["_source"] = self._source
        return result


@dataclass
class Program:
    """An EPG programme entry."""

    title: str = ""
    start: str = ""
    stop: str = ""
    desc: str = ""
    channel: str = ""


@dataclass
class PlaylistSource:
    """Metadata about a loaded playlist source."""

    path: str = ""
    source_type: str = "m3u"
    channel_count: int = 0
    label: str = ""
