"""Favorite channels management with persistent storage and event integration."""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path

from . import core

logger = logging.getLogger(__name__)


class FavoritesManager:
    """Manage favorite channels with persistence and event notification."""
    
    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = data_dir or Path.home() / ".config" / "symoneural-view"
        self.favorites_file = self.data_dir / "favorites.json"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.favorites: dict[str, list[str]] = {}
        self.lock = threading.Lock()
        self.load()
    
    def load(self) -> None:
        """Load favorites from disk."""
        with self.lock:
            if self.favorites_file.exists():
                try:
                    with open(self.favorites_file, 'r', encoding='utf-8') as f:
                        self.favorites = json.load(f)
                    total = sum(len(v) for v in self.favorites.values())
                    logger.info(f"Loaded {total} favorites")
                except Exception as e:
                    logger.error(f"Favorites load failed: {e}")
    
    def save(self) -> None:
        """Save favorites to disk."""
        with self.lock:
            try:
                with open(self.favorites_file, 'w', encoding='utf-8') as f:
                    json.dump(self.favorites, f, indent=2)
                event_bus = core.get_event_bus()
                if event_bus:
                    event_bus.emit("favorites_changed", self.favorites.copy())
                logger.debug("Favorites saved")
            except Exception as e:
                logger.error(f"Favorites save failed: {e}")
    
    def add_favorite(self, category: str, channel_id: str) -> bool:
        """Add channel to favorites."""
        with self.lock:
            if category not in self.favorites:
                self.favorites[category] = []
            
            if channel_id not in self.favorites[category]:
                self.favorites[category].append(channel_id)
                self.save()
                logger.debug(f"Added favorite: {category}/{channel_id}")
                return True
        return False
    
    def remove_favorite(self, category: str, channel_id: str) -> bool:
        """Remove channel from favorites."""
        with self.lock:
            if category in self.favorites and channel_id in self.favorites[category]:
                self.favorites[category].remove(channel_id)
                if not self.favorites[category]:
                    del self.favorites[category]
                self.save()
                logger.debug(f"Removed favorite: {category}/{channel_id}")
                return True
        return False
    
    def is_favorite(self, category: str, channel_id: str) -> bool:
        """Check if channel is favorited."""
        with self.lock:
            return channel_id in self.favorites.get(category, [])
    
    def get_favorites(self, category: str | None = None) -> dict[str, list[str]]:
        """Get favorites, optionally by category."""
        with self.lock:
            if category:
                return {category: self.favorites.get(category, [])}
            return self.favorites.copy()
    
    def add_bulk(self, items: dict[str, list[str]]) -> None:
        """Add multiple favorites at once."""
        with self.lock:
            for category, channel_ids in items.items():
                if category not in self.favorites:
                    self.favorites[category] = []
                for ch_id in channel_ids:
                    if ch_id not in self.favorites[category]:
                        self.favorites[category].append(ch_id)
            self.save()
    
    def clear(self, category: str | None = None) -> None:
        """Clear favorites."""
        with self.lock:
            if category:
                if category in self.favorites:
                    del self.favorites[category]
            else:
                self.favorites.clear()
            self.save()