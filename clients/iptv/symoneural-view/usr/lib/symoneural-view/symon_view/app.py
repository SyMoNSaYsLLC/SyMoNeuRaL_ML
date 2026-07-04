"""SyMoNeuRaL-View application entry point.

Handles CLI arguments, application bootstrap, source selection,
and the main event loop.
"""

from __future__ import annotations

import argparse
import atexit
import gzip
import logging
import os
import signal
import sys
import zipfile
from pathlib import Path
from types import FrameType
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CLI helpers
# ---------------------------------------------------------------------------

def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(prog="symoneural-view")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument(
        "--health-check", dest="health_check", action="store_true", help="Run health check"
    )
    parser.add_argument("--diagnostic", action="store_true", help="Run diagnostics")
    parser.add_argument("--reset", action="store_true", help="Reset settings to defaults")
    return parser.parse_args()


def _signal_handler(signum: int, frame: Optional[FrameType]) -> None:
    _ = frame
    logger.info("Received signal %d, exiting...", signum)
    raise SystemExit(0)


def setup_signal_handlers() -> None:
    """Install SIGINT / SIGTERM handlers."""
    try:
        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)
    except Exception as exc:
        logger.debug("Signal handler setup skipped: %s", exc)


# ---------------------------------------------------------------------------
# CLI sub-commands
# ---------------------------------------------------------------------------

def handle_health_check() -> int:
    """Print a simple health status and exit."""
    print("health: ok")
    return 0


def handle_diagnostic() -> int:
    """Run diagnostics and exit."""
    try:
        from .diagnostic_tools import DiagnosticReport

        report = {"status": "ok"}
        if hasattr(DiagnosticReport, "print_report"):
            DiagnosticReport.print_report(report)  # type: ignore[attr-defined]
        print("diagnostic: ok")
        return 0
    except Exception as exc:
        logger.error("Diagnostic failed: %s", exc)
        print(f"diagnostic: failed ({exc})")
        return 1


def handle_reset() -> int:
    """Reset settings to defaults and exit."""
    try:
        from .core import Settings

        settings = Settings()
        settings.reset_to_defaults()
        logger.info("Settings reset to defaults")
        return 0
    except Exception as exc:
        logger.error("Failed to reset settings: %s", exc)
        print(f"Error: failed to reset settings ({exc})")
        return 1


# ---------------------------------------------------------------------------
# Source loaders (Xtream / M3U)
# ---------------------------------------------------------------------------

JsonDict = dict[str, Any]
Channel = dict[str, Any]


def _read_xmltv_file(path: str) -> str:
    """Read XMLTV content from .xml, .gz, or .zip."""
    p = Path(path)
    suffix = p.suffix.lower()

    if suffix == ".gz":
        with gzip.open(p, "rt", encoding="utf-8", errors="ignore") as f:
            return f.read()

    if suffix == ".zip":
        with zipfile.ZipFile(p, "r") as zf:
            xml_candidates = [n for n in zf.namelist() if n.lower().endswith(".xml")]
            if not xml_candidates:
                raise ValueError("ZIP does not contain an XML file")
            with zf.open(xml_candidates[0], "r") as f:
                return f.read().decode("utf-8", errors="ignore")

    return p.read_text(encoding="utf-8", errors="ignore")


def handle_xtream_source(
    settings: Any,
) -> tuple[list[Channel] | None, JsonDict, Any]:
    """Handle Xtream API source with recovery.

    Returns:
        (channels, epg_index, xdp_object) or (None, {}, None) on failure.
    """
    from PyQt6.QtWidgets import QDialog, QMessageBox

    from . import interface, parsers

    login = interface.XtreamLoginDialog(settings.data if hasattr(settings, "data") else settings)
    if login.exec() != QDialog.DialogCode.Accepted:
        return None, {}, None

    host, user, pw = login.get_credentials()
    if not all([host, user, pw]):
        QMessageBox.warning(None, "Error", "All fields required")
        return None, {}, None

    try:
        if hasattr(settings, "set_many"):
            settings.set_many({"xtream_host": host, "xtream_user": user, "xtream_pass": pw})

        client = parsers.XtreamAPI(host, user, pw, max_retries=3)
        channels: list[Channel] = []

        for item in client.fetch_live_streams() or []:
            channels.append({
                "name": item.get("name", "Unknown"),
                "url": f"{host.rstrip('/')}/live/{user}/{pw}/{item.get('stream_id')}.ts",
                "logo": item.get("stream_icon"),
                "group": item.get("category_name", "Live TV"),
                "tvg_id": item.get("epg_channel_id"),
                "stream_id": item.get("stream_id"),
                "catchup": {
                    "enabled": item.get("tv_archive") == 1,
                    "days": int(item.get("tv_archive_duration") or 0),
                },
                "_source": "xtream_live",
            })

        for item in client.fetch_vod_streams() or []:
            channels.append({
                "name": item.get("name", "Unknown"),
                "url": f"{host.rstrip('/')}/movie/{user}/{pw}/{item.get('stream_id')}.mp4",
                "logo": item.get("stream_icon"),
                "group": "VOD",
                "tvg_id": item.get("stream_id"),
                "_source": "xtream_vod",
            })

        for item in client.fetch_series() or []:
            channels.append({
                "name": item.get("name", "Unknown"),
                "logo": item.get("cover"),
                "group": "Series",
                "tvg_id": item.get("series_id"),
                "_source": "xtream_series",
            })

        if not channels:
            QMessageBox.warning(None, "No Content", "No content found on Xtream server")
            return None, {}, None

        xmltv = parsers.fetch_xtream_xmltv(host, user, pw)
        epg_data: JsonDict = {}
        if xmltv:
            epg_data = parsers.XMLTVParser.parse(xmltv)

        epg_index = parsers.merge_epg(channels, epg_data, {"host": host, "user": user, "pw": pw})
        return channels, epg_index, None

    except Exception as exc:
        logger.exception("Xtream source error")
        QMessageBox.critical(None, "Connection Error", f"Failed to connect to Xtream:\n{exc}")
        return None, {}, None


def handle_m3u_source() -> tuple[list[Channel], JsonDict]:
    """Handle M3U source with optional multi-file loading.

    Returns:
        (channels, epg_index).
    """
    from PyQt6.QtWidgets import QFileDialog, QMessageBox

    from . import parsers

    channels: list[Channel] = []

    while True:
        path, _ = QFileDialog.getOpenFileName(
            None,
            "Select M3U Playlist",
            "",
            "Playlists (*.m3u *.m3u8);;All Files (*)",
        )
        if not path:
            break

        try:
            channels.extend(parsers.M3UParser.parse(path))
        except Exception as exc:
            logger.exception("M3U parse error for %s", path)
            QMessageBox.warning(None, "Error", f"Failed to parse {path}:\n{exc}")
            continue

        from PyQt6.QtWidgets import QMessageBox as _MB

        reply = _MB.question(
            None,
            "Add Another",
            f"Loaded {len(channels)} channels. Add another playlist?",
            _MB.StandardButton.Yes | _MB.StandardButton.No,
        )
        if reply == _MB.StandardButton.No:
            break

    if not channels:
        QMessageBox.warning(None, "No Content", "No channels loaded")
        return [], {}

    guide: JsonDict = {}
    xml_path, _ = QFileDialog.getOpenFileName(
        None, "Select XMLTV EPG (optional)", "", "XMLTV Files (*.xml *.gz *.zip)"
    )
    if xml_path:
        try:
            guide = parsers.XMLTVParser.parse(_read_xmltv_file(xml_path))
        except Exception as exc:
            logger.exception("XMLTV parse error for %s", xml_path)
            QMessageBox.warning(None, "Error", f"Failed to parse EPG:\n{exc}")

    epg_index = parsers.merge_epg(channels, guide)
    return channels, epg_index


# ---------------------------------------------------------------------------
# Cleanup & shutdown
# ---------------------------------------------------------------------------

_playback_engine: Any = None
_main_window: Any = None
_inhibitor: Any = None
_cleanup_done = False


def _cleanup_resources() -> None:
    """Release playback / inhibitor resources."""
    global _cleanup_done
    if _cleanup_done:
        return
    _cleanup_done = True

    try:
        if _playback_engine and hasattr(_playback_engine, "cleanup"):
            _playback_engine.cleanup()
    except Exception:
        logger.exception("Playback cleanup failed")

    try:
        if _inhibitor and hasattr(_inhibitor, "uninhibit"):
            _inhibitor.uninhibit()
    except Exception:
        logger.exception("Inhibitor cleanup failed")


def shutdown() -> None:
    """Clean shutdown handler."""
    logger.info("SyMoNeuRaL shutting down...")
    try:
        _cleanup_resources()
        if _main_window and hasattr(_main_window, "close"):
            _main_window.close()
    except Exception:
        logger.exception("Shutdown error")
    logger.info("Shutdown complete")


def reset_setup(app: Any) -> None:
    """Reset configuration and restart the application."""
    try:
        from .core import get_settings

        settings = get_settings()
        settings.reset_to_defaults()
        logger.info("Settings reset. Restarting...")
        if app:
            app.quit()
        os.execvp(sys.argv[0], sys.argv)
    except Exception as exc:
        logger.exception("Reset failed")
        from PyQt6.QtWidgets import QMessageBox

        QMessageBox.critical(None, "Error", f"Reset failed: {exc}")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main() -> int | None:
    """Application entry point.

    Returns:
        Exit code, or *None* if no window was launched.
    """
    global _playback_engine, _main_window, _inhibitor

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    args = parse_arguments()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")

    if args.health_check:
        return handle_health_check()

    if args.diagnostic:
        return handle_diagnostic()

    if args.reset:
        return handle_reset()

    # --- GUI bootstrap ---
    setup_signal_handlers()
    atexit.register(shutdown)

    from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox

    from .core import CHANNELS_LOADED, get_event_bus, get_settings
    from . import interface, parsers

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("SyMoNeuRaL")
    app.setOrganizationName("SyMoNeuRaL")
    app.setApplicationVersion("2.2.0")

    logger.info("Starting SyMoNeuRaL v2.2.0")

    settings = get_settings()

    # First-run wizard
    if settings.get("organization_style") is None:
        wiz = interface.IntelligenceWizard()
        if wiz.exec() != QDialog.DialogCode.Accepted:
            return None
        cfg = wiz.get_config()
        settings.set_many({
            "organization_style": cfg.get("style", "smart"),
            "xdp": cfg.get("xdp", False),
        })

    # Source selection
    source = interface.SourceSelectDialog()
    if source.exec() != QDialog.DialogCode.Accepted:
        return None

    channels: list[Channel] | None = None
    epg_index: JsonDict = {}
    xtream_creds: dict[str, str] | None = None

    if source.is_xtream():
        channels, epg_index, _ = handle_xtream_source(settings)
        if channels is None:
            return None
        xtream_creds = {
            "host": settings.get("xtream_host", ""),
            "user": settings.get("xtream_user", ""),
            "pw": settings.get("xtream_pass", ""),
        }
    else:
        channels, epg_index = handle_m3u_source()
        if not channels:
            return None

    # Preferences dialog (optional AI personalization)
    try:
        from .dialogs import PreferencesDialog, PlaylistSegmentDialog

        pref_dialog = PreferencesDialog()
        if pref_dialog.exec() == QDialog.DialogCode.Accepted:
            preferences = pref_dialog.get_preferences()
            if preferences is not None and channels:
                segment_dialog = PlaylistSegmentDialog(channels, epg_index, preferences)
                segment_dialog.exec()
    except ImportError:
        logger.debug("Dialogs module not available, skipping preferences")

    # Main window
    window_kwargs: dict[str, Any] = {}
    if xtream_creds:
        window_kwargs["xtream_creds"] = xtream_creds

    _main_window = interface.SymonWindow(
        settings.data,
        on_reset=lambda: reset_setup(app),
        **window_kwargs,
    )
    _playback_engine = getattr(_main_window, "playback", None)
    _inhibitor = getattr(_main_window, "inhibitor", None)

    # Organize & populate
    organization_style = settings.get("organization_style") or "smart"
    data_map = parsers.organize_channels(channels, organization_style)

    if not data_map:
        QMessageBox.warning(None, "Error", "No media available after processing")
        return None

    get_event_bus().emit(CHANNELS_LOADED, data_map)

    populate = getattr(_main_window, "populate_workstation", None)
    if callable(populate):
        try:
            populate(data_map, epg_index)
        except Exception:
            logger.debug("populate_workstation not applicable")

    _main_window.show()

    rc = app.exec()
    _cleanup_resources()
    return rc


if __name__ == "__main__":
    sys.exit(main() or 0)
