"""SyMoNeuRaL core infrastructure.

Provides the event bus, settings manager, and module-level singletons
shared by every other module in the package.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from collections import defaultdict
from enum import Enum
from pathlib import Path
from typing import Any, Callable, DefaultDict

logger = logging.getLogger(__name__)

EventCallback = Callable[[Any], None]


class EventType(str, Enum):
    PLAYBACK_STARTED = "playback_started"
    PLAYBACK_PAUSED = "playback_paused"
    PLAYBACK_STOPPED = "playback_stopped"
    ERROR_OCCURRED = "error_occurred"
    SETTINGS_CHANGED = "settings_changed"
    CHANNELS_LOADED = "channels_loaded"
    CACHE_INVALIDATED = "cache_invalidated"
    RECORDING_STARTED = "recording_started"
    RECORDING_STOPPED = "recording_stopped"


# Backward-compatible symbol used by older code.
CHANNELS_LOADED = EventType.CHANNELS_LOADED


class EventBus:
    """Thread-safe publish/subscribe event bus."""

    def __init__(self) -> None:
        self._subs: DefaultDict[str, list[EventCallback]] = defaultdict(list)
        self._lock = threading.RLock()

    def subscribe(self, event: str | EventType, callback: EventCallback) -> None:
        key = event.value if isinstance(event, EventType) else str(event)
        with self._lock:
            self._subs[key].append(callback)

    def unsubscribe(self, event: str | EventType, callback: EventCallback) -> None:
        key = event.value if isinstance(event, EventType) else str(event)
        with self._lock:
            callbacks = self._subs.get(key)
            if not callbacks:
                return
            if callback in callbacks:
                callbacks.remove(callback)
            if not callbacks:
                self._subs.pop(key, None)

    def emit(self, event: str | EventType, payload: Any = None) -> None:
        key = event.value if isinstance(event, EventType) else str(event)
        with self._lock:
            callbacks = list(self._subs.get(key, []))
        for cb in callbacks:
            try:
                cb(payload)
            except Exception:
                logger.exception("Event callback error for '%s'", key)


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

_DEFAULTS: dict[str, Any] = {
    "playback_backend": "vlc",
    "volume": 75,
    "http_remote_enabled": True,
    "http_remote_port": 8080,
    "http_remote_bind": "127.0.0.1",
    "organization_style": "smart",
    "xdp": False,
}


class Settings:
    """Thread-safe settings manager with JSON persistence."""

    def __init__(self, path: Path | None = None) -> None:
        config_home = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        base_dir = config_home / "symoneural-view"
        self.path = path or (base_dir / "settings.json")
        self._lock = threading.RLock()
        self._data: dict[str, Any] = dict(_DEFAULTS)
        self._load()

    @property
    def data(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._data)

    def _load(self) -> None:
        with self._lock:
            if not self.path.exists():
                return
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    self._data.update(raw)
                else:
                    logger.warning("Settings file is not a JSON object: %s", self.path)
            except Exception:
                logger.exception("Settings load failed: %s", self.path)

    def save(self) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = self.path.with_suffix(f"{self.path.suffix}.tmp")
            tmp_path.write_text(
                json.dumps(self._data, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            tmp_path.replace(self.path)

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._data.get(key, default)

    def set(self, key: str, value: Any, emit: bool = True) -> None:
        with self._lock:
            self._data[key] = value
            self.save()
        if emit:
            get_event_bus().emit(EventType.SETTINGS_CHANGED, {"key": key, "value": value})

    def set_many(self, values: dict[str, Any], emit: bool = True) -> None:
        self.update(values, emit=emit)

    def update(self, values: dict[str, Any], emit: bool = True) -> None:
        with self._lock:
            self._data.update(values)
            self.save()
        if emit:
            get_event_bus().emit(EventType.SETTINGS_CHANGED, dict(values))

    def all(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._data)

    def reset_to_defaults(self) -> None:
        with self._lock:
            self._data = dict(_DEFAULTS)
            self.save()
        get_event_bus().emit(EventType.SETTINGS_CHANGED, self.all())

    # Backward-compatible alias.
    def reset(self) -> None:
        self.reset_to_defaults()


# ---------------------------------------------------------------------------
# Module-level singletons
# ---------------------------------------------------------------------------

_event_bus = EventBus()
_settings: Settings | None = None
_settings_lock = threading.Lock()


def get_event_bus() -> EventBus:
    """Return the shared EventBus instance."""
    return _event_bus


def get_settings() -> Settings:
    """Return the shared Settings instance (created on first call)."""
    global _settings
    with _settings_lock:
        if _settings is None:
            _settings = Settings()
        return _settings


def save_settings(data: dict[str, Any]) -> None:
    """Persist a plain dict into the settings store."""
    settings = get_settings()
    settings.update(data, emit=False)
