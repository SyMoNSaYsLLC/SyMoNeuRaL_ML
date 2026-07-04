"""System inhibition for screensaver/sleep prevention with auto-activation."""

from __future__ import annotations

import logging
from typing import Any

try:
    import dbus as _dbus  # type: ignore[reportMissingImports]
except Exception:
    _dbus = None

dbus: Any = _dbus

from . import core

logger = logging.getLogger(__name__)

# Ensure core.EventType is available
if not hasattr(core, 'EventType'):
    raise ImportError("EventType not found in core module")


class InhibitManager:
    """Manage system inhibitions (screensaver, sleep) with fallbacks."""
    
    def __init__(self):
        self.inhibit_cookie: int | None = None
        self.backend = None
        self.bus = None
        self._init_backend()
        self._setup_event_handlers()
    
    def _init_backend(self) -> None:
        """Initialize inhibition backend with fallbacks."""
        backends_to_try = [
            ("logind", self._init_logind),
            ("gnome_screensaver", self._init_gnome),
            ("xdg_idle", self._init_xdg)
        ]
        
        for backend_name, init_func in backends_to_try:
            try:
                init_func()
                self.backend = backend_name
                logger.info(f"{backend_name} backend available")
                return
            except Exception as e:
                logger.debug(f"{backend_name} unavailable: {e}")
        
        logger.warning("No inhibition backend available")
    
    def _init_logind(self) -> None:
        """Initialize systemd logind backend."""
        if dbus is None:
            raise ImportError("dbus module not available")
        self.bus = dbus.SessionBus()
        # Test connection
        self.bus.get_object("org.freedesktop.login1", "/org/freedesktop/login1")
    
    def _init_gnome(self) -> None:
        """Initialize GNOME Screensaver backend."""
        if dbus is None:
            raise ImportError("dbus module not available")
        self.bus = dbus.SessionBus()
        self.bus.get_object("org.gnome.ScreenSaver", "/org/gnome/ScreenSaver")
    
    def _init_xdg(self) -> None:
        """Initialize XDG idle backend (fallback)."""
        # This is a placeholder for XDG idle inhibition
        pass
    
    def _setup_event_handlers(self) -> None:
        """Setup event handlers for auto-activation."""
        bus = core.get_event_bus()
        if bus is None:
            logger.warning("Event bus not available, skipping event handler setup")
            return
        if not hasattr(core, 'EventType') or core.EventType is None:
            logger.warning("EventType not available, skipping event handler setup")
            return
        bus.subscribe(core.EventType.PLAYBACK_STARTED, self._on_playback_started)
        bus.subscribe(core.EventType.PLAYBACK_STOPPED, self._on_playback_stopped)
        bus.subscribe(core.EventType.RECORDING_STARTED, self._on_recording_started)
        bus.subscribe(core.EventType.RECORDING_STOPPED, self._on_recording_stopped)
    
    def _on_playback_started(self, url: str) -> None:
        """Auto-inhibit on playback start."""
        try:
            should_inhibit = True
            settings = self._get_inhibit_setting()
            if settings is not None:
                should_inhibit = settings
            if should_inhibit:
                self.inhibit("Playing media")
        except Exception as e:
            logger.debug(f"Failed to get settings: {e}")
    
    def _on_playback_stopped(self, *args) -> None:
        """Remove inhibition on playback stop."""
        self.uninhibit()
    
    def _on_recording_started(self, *args) -> None:
        """Auto-inhibit on recording start."""
        try:
            should_inhibit = True
            settings = self._get_inhibit_setting()
            if settings is not None:
                should_inhibit = settings
            if should_inhibit:
                self.inhibit("Recording in progress")
        except Exception as e:
            logger.debug(f"Failed to get settings: {e}")
    
    def _on_recording_stopped(self, *args) -> None:
        """Remove inhibition on recording stop."""
        self.uninhibit()
    
    def _get_inhibit_setting(self) -> bool | None:
        """Get the enable_inhibit setting from core module."""
        try:
            # Try to get settings if the function exists
            if hasattr(core, 'get_settings'):
                get_settings_func = getattr(core, 'get_settings', None)
                if callable(get_settings_func):
                    settings = get_settings_func()
                    if settings and isinstance(settings, dict):
                        return settings.get("enable_inhibit", True)
        except Exception as e:
            logger.debug(f"Failed to get settings: {e}")
        return True  # Default to inhibiting if we can't determine setting
    
    def inhibit(self, reason: str = "SyMoNeuRaL is active") -> bool:
        """Inhibit screensaver/sleep."""
        if not self.backend:
            logger.debug("No inhibition backend available")
            return False
        
        try:
            if self.inhibit_cookie is not None:
                return True  # Already inhibited
            
            if self.backend == "logind":
                return self._inhibit_logind(reason)
            elif self.backend == "gnome_screensaver":
                return self._inhibit_gnome(reason)
            elif self.backend == "xdg_idle":
                return self._inhibit_xdg(reason)
        except Exception as e:
            logger.error(f"Inhibit failed: {e}")
        
        return False
    
    def _inhibit_logind(self, reason: str) -> bool:
        """Use systemd logind for inhibition."""
        try:
            if dbus is None:
                raise ImportError("dbus module not available")
            if self.bus is None:
                raise RuntimeError("D-Bus connection not available")
            logind = self.bus.get_object("org.freedesktop.login1",
                                        "/org/freedesktop/login1")
            inhibit_method = logind.get_dbus_method("Inhibit",
                                                   "org.freedesktop.login1.Manager")
            
            self.inhibit_cookie = inhibit_method("sleep:idle", "symoneural",
                                                reason, "block")
            logger.debug(f"Inhibited: {reason}")
            return True
        except Exception as e:
            logger.error(f"logind inhibit failed: {e}")
            return False
    
    def _inhibit_gnome(self, reason: str) -> bool:
        """Use GNOME screensaver for inhibition."""
        try:
            if dbus is None:
                raise ImportError("dbus module not available")
            if self.bus is None:
                raise RuntimeError("D-Bus connection not available")
            screensaver = self.bus.get_object("org.gnome.ScreenSaver",
                                             "/org/gnome/ScreenSaver")
            inhibit_method = screensaver.get_dbus_method("Inhibit",
                                                        "org.gnome.ScreenSaver")
            
            self.inhibit_cookie = inhibit_method("symoneural", reason)
            logger.debug(f"Inhibited: {reason}")
            return True
        except Exception as e:
            logger.error(f"GNOME inhibit failed: {e}")
            return False
    
    def _inhibit_xdg(self, reason: str) -> bool:
        """Use XDG idle inhibition (fallback)."""
        # Placeholder implementation
        logger.debug(f"XDG inhibit: {reason}")
        return True
    
    def uninhibit(self) -> bool:
        """Remove inhibition."""
        if not self.backend or self.inhibit_cookie is None:
            return False
        
        try:
            if self.backend == "logind":
                return self._uninhibit_logind()
            elif self.backend == "gnome_screensaver":
                return self._uninhibit_gnome()
        except Exception as e:
            logger.error(f"Uninhibit failed: {e}")
        
        return False
    
    def _uninhibit_logind(self) -> bool:
        """Remove logind inhibition."""
        try:
            if dbus is None:
                raise ImportError("dbus module not available")
            if self.bus is None:
                logger.error("D-Bus connection not available")
                return False
            logind = self.bus.get_object("org.freedesktop.login1",
                                        "/org/freedesktop/login1")
            close_method = logind.get_dbus_method("Close",
                                                 "org.freedesktop.login1.Manager")
            
            close_method(self.inhibit_cookie)
            self.inhibit_cookie = None
            logger.debug("Inhibition removed")
            return True
        except Exception as e:
            logger.error(f"logind close failed: {e}")
            return False
    
    def _uninhibit_gnome(self) -> bool:
        """Remove GNOME screensaver inhibition."""
        try:
            if dbus is None:
                raise ImportError("dbus module not available")
            if self.bus is None:
                logger.error("D-Bus connection not available")
                return False
            screensaver = self.bus.get_object("org.gnome.ScreenSaver",
                                             "/org/gnome/ScreenSaver")
            uninhibit_method = screensaver.get_dbus_method("UnInhibit",
                                                          "org.gnome.ScreenSaver")
            
            uninhibit_method(self.inhibit_cookie)
            self.inhibit_cookie = None
            logger.debug("Inhibition removed")
            return True
        except Exception as e:
            logger.error(f"GNOME close failed: {e}")
            return False
