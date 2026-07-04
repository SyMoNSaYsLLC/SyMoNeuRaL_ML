"""Advanced keyboard bindings and input handling."""

from __future__ import annotations

import json
import logging
import threading
from enum import Enum
from pathlib import Path
from typing import Callable

from PyQt6.QtGui import QKeySequence

logger = logging.getLogger(__name__)


class KeyContext(Enum):
    """Key binding contexts."""
    GLOBAL = "global"
    PLAYBACK = "playback"
    SEARCH = "search"
    SETTINGS = "settings"


# Default bindings for backward compatibility
DEFAULT_BINDINGS = {
    "play_pause": "Space",
    "next_channel": "Right",
    "prev_channel": "Left",
    "volume_up": "Up",
    "volume_down": "Down",
    "mute": "M",
    "favorites": "F",
    "record": "R",
    "info": "I",
    "settings": "S",
    "quit": "Ctrl+Q",
    "search": "Ctrl+F",
    "fullscreen": "F11",
    "overlay": "Ctrl+O",
    "seek_forward": "Ctrl+Right",
    "seek_backward": "Ctrl+Left",
}

# Backward-compatible alias
DEFAULT_BINDS = DEFAULT_BINDINGS


class KeybindManager:
    """Manage keyboard shortcuts."""
    
    DEFAULT_BINDINGS = DEFAULT_BINDINGS
    DEFAULT_BINDS = DEFAULT_BINDS
    
    def __init__(self, config_file: Path):
        self.config_file = Path(config_file)
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.bindings: dict[str, str] = self.DEFAULT_BINDINGS.copy()
        self.handlers: dict[str, list[Callable]] = {}
        self.lock = threading.RLock()
        self.context = KeyContext.GLOBAL
        
        self._load_config()
        logger.info("KeybindManager initialized")
    
    def _load_config(self) -> None:
        """Load keybindings from config."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    self.bindings.update(loaded)
                logger.debug(f"Loaded {len(loaded)} custom keybindings")
            except Exception as e:
                logger.error(f"Failed to load keybindings: {e}")
    
    def _save_config(self) -> None:
        """Save keybindings to config."""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.bindings, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save keybindings: {e}")
    
    def register_action(self, action: str, handler: Callable,
                       context: KeyContext = KeyContext.GLOBAL) -> None:
        """Register action handler."""
        with self.lock:
            if action not in self.handlers:
                self.handlers[action] = []
            self.handlers[action].append(handler)
            logger.debug(f"Registered action: {action}")
    
    def unregister_action(self, action: str, handler: Callable) -> None:
        """Unregister action handler."""
        with self.lock:
            if action in self.handlers and handler in self.handlers[action]:
                self.handlers[action].remove(handler)
    
    def execute_action(self, action: str, *args, **kwargs) -> None:
        """Execute action handlers."""
        with self.lock:
            if action in self.handlers:
                for handler in self.handlers[action]:
                    try:
                        handler(*args, **kwargs)
                    except Exception as e:
                        logger.error(f"Action handler error: {e}")
    
    def set_binding(self, action: str, key_sequence: str) -> bool:
        """Set custom keybinding."""
        try:
            seq = QKeySequence.fromString(key_sequence)
            if seq.isEmpty():
                logger.warning(f"Invalid key sequence: {key_sequence}")
                return False
            
            with self.lock:
                self.bindings[action] = key_sequence
                self._save_config()
            
            logger.info(f"Set keybinding: {action} = {key_sequence}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to set binding: {e}")
            return False
    
    def get_binding(self, action: str) -> str | None:
        """Get keybinding for action."""
        with self.lock:
            return self.bindings.get(action)
    
    def get_all_bindings(self) -> dict[str, str]:
        """Get all keybindings."""
        with self.lock:
            return self.bindings.copy()
    
    def reset_to_defaults(self) -> None:
        """Reset to default keybindings."""
        with self.lock:
            self.bindings = self.DEFAULT_BINDINGS.copy()
            self._save_config()
        logger.info("Keybindings reset to defaults")
    
    def import_from_file(self, filepath: Path) -> bool:
        """Import keybindings from file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                imported = json.load(f)
            
            with self.lock:
                self.bindings.update(imported)
                self._save_config()
            
            logger.info(f"Imported {len(imported)} keybindings")
            return True
        
        except Exception as e:
            logger.error(f"Import failed: {e}")
            return False
    
    def export_to_file(self, filepath: Path) -> bool:
        """Export keybindings to file."""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.bindings, f, indent=2)
            
            logger.info(f"Exported keybindings to {filepath}")
            return True
        
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return False
