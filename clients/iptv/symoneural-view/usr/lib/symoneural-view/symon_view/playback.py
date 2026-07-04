"""Media playback engine with VLC fallback subprocess backend."""

from __future__ import annotations

import logging
import subprocess
import threading
from typing import Any

from . import core

logger = logging.getLogger(__name__)


class PlaybackEngine:
    """Simple, robust playback engine."""

    BACKENDS = ["vlc", "subprocess"]

    def __init__(self, backend: str | None = None):
        settings = core.get_settings()
        configured = backend or settings.get("playback_backend", "vlc")
        self.backend = str(configured).lower()

        self.instance: Any = None
        self.player: Any = None
        self.media_player: Any = None
        self.current_media: Any = None
        self.current_url: str | None = None
        self.is_playing = False
        self.lock = threading.RLock()
        self._proc: subprocess.Popen | None = None

        self._init_backend()

    def _emit_event(self, name: str, payload: Any = None) -> None:
        try:
            bus = core.get_event_bus()
            event_type = getattr(core, "EventType", None)
            event = getattr(event_type, name, name) if event_type else name
            if payload is None:
                bus.emit(event)
            else:
                bus.emit(event, payload)
        except Exception as e:
            logger.debug(f"Event emit skipped ({name}): {e}")

    def _init_backend(self) -> None:
        if self.backend != "vlc":
            self.backend = "subprocess"
            logger.info("Using subprocess backend")
            return

        try:
            import vlc  # type: ignore

            self.instance = vlc.Instance("--quiet")
            self.player = self.instance.media_list_player_new()
            self.media_player = self.player.get_media_player()
            logger.info("VLC backend initialized")
        except Exception as e:
            logger.warning(f"VLC init failed, fallback to subprocess: {e}")
            self.backend = "subprocess"
            self.instance = None
            self.player = None
            self.media_player = None

    def play(self, url: str, options: dict[str, Any] | None = None) -> bool:
        with self.lock:
            try:
                if not url:
                    return False

                self.stop()

                ok = self._play_vlc(url, options) if self.backend == "vlc" else self._play_subprocess(url, options)
                if ok:
                    self.is_playing = True
                    self.current_url = url
                    self._emit_event("PLAYBACK_STARTED", url)
                return ok
            except Exception as e:
                logger.error(f"Playback error: {e}")
                self._emit_event("ERROR_OCCURRED", f"Playback failed: {e}")
                return False

    def _play_vlc(self, url: str, options: dict[str, Any] | None = None) -> bool:
        try:
            if not self.instance or not self.player:
                return False

            media = self.instance.media_new(url)
            if options:
                for k, v in options.items():
                    media.add_option(f"--{k}={v}")

            media_list = self.instance.media_list_new()
            media_list.add_media(media)
            self.player.set_media_list(media_list)
            self.player.play()

            self.current_media = media
            return True
        except Exception as e:
            logger.error(f"VLC playback failed: {e}")
            return False

    def _play_subprocess(self, url: str, options: dict[str, Any] | None = None) -> bool:
        try:
            cmd = ["vlc", "--quiet", url]
            if options:
                for k, v in options.items():
                    cmd.append(f"--{k}={v}")

            self._proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception as e:
            logger.error(f"Subprocess playback failed: {e}")
            return False

    def pause(self) -> None:
        with self.lock:
            try:
                if self.backend == "vlc" and self.player:
                    self.player.pause()
                self._emit_event("PLAYBACK_PAUSED")
            except Exception as e:
                logger.error(f"Pause failed: {e}")

    def stop(self) -> None:
        with self.lock:
            try:
                if self.backend == "vlc" and self.player:
                    self.player.stop()

                if self._proc and self._proc.poll() is None:
                    self._proc.terminate()
                    try:
                        self._proc.wait(timeout=2)
                    except Exception:
                        self._proc.kill()
                self._proc = None

                self.is_playing = False
                self.current_url = None
                self.current_media = None
                self._emit_event("PLAYBACK_STOPPED")
            except Exception as e:
                logger.error(f"Stop failed: {e}")

    def set_volume(self, level: int) -> bool:
        with self.lock:
            try:
                level = max(0, min(100, int(level)))

                if self.backend == "vlc" and self.media_player:
                    self.media_player.audio_set_volume(level)

                settings = core.get_settings()
                try:
                    settings.set("volume", level, emit=False)
                except TypeError:
                    settings.set("volume", level)
                return True
            except Exception as e:
                logger.error(f"Volume control failed: {e}")
                return False

    def set_subtitle(self, path: str) -> bool:
        with self.lock:
            try:
                if self.backend == "vlc" and self.media_player:
                    self.media_player.video_set_subtitle_file(path)
                    logger.info(f"Subtitle loaded: {path}")
                    return True
                return False
            except Exception as e:
                logger.error(f"Subtitle loading failed: {e}")
                return False

    def get_diagnostics(self) -> dict[str, Any]:
        return {
            "backend": self.backend,
            "is_playing": self.is_playing,
            "current_url": self.current_url,
            "has_player": self.player is not None or self._proc is not None,
        }

    def cleanup(self) -> None:
        try:
            self.stop()
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")

    def __del__(self) -> None:
        try:
            self.cleanup()
        except Exception:
            pass