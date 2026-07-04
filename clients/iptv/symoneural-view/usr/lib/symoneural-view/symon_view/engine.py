"""AI Analysis engine with event integration and preference learning."""

from __future__ import annotations

import logging

from PyQt6.QtCore import QThread, pyqtSignal

from . import core

logger = logging.getLogger(__name__)

# Safe fallbacks for EventType attributes
try:
    from .core import EventType
    CHANNELS_LOADED_EVENT = EventType.CHANNELS_LOADED.value if hasattr(EventType, "CHANNELS_LOADED") else "channels_loaded"
    ERROR_OCCURRED_EVENT = EventType.ERROR_OCCURRED.value if hasattr(EventType, "ERROR_OCCURRED") else "error_occurred"
except (ImportError, AttributeError):
    CHANNELS_LOADED_EVENT = "channels_loaded"
    ERROR_OCCURRED_EVENT = "error_occurred"


class PlaylistAnalyzer(QThread):
    """Advanced AI playlist analyzer with preference learning."""
    
    progress = pyqtSignal(str, int)  # (message, percentage)
    finished = pyqtSignal(dict)      # (categorized_data)
    
    # Configurable category rules
    CATEGORY_RULES = {
        "live": {
            "keywords": ["live", "tv", "channel", "stream"],
            "has_url": True,
            "priority": 5
        },
        "vod": {
            "keywords": ["vod", "video", "movie", "film"],
            "has_url": True,
            "priority": 4
        },
        "series": {
            "keywords": ["series", "season", "episode", "show"],
            "has_url": False,
            "priority": 3
        },
        "kids": {
            "keywords": ["kids", "cartoon", "disney", "nick", "child", "junior"],
            "priority": 10
        },
        "sports": {
            "keywords": ["sport", "espn", "nba", "nfl", "soccer", "football", "nhl"],
            "priority": 8
        },
        "news": {
            "keywords": ["news", "cnn", "bbc", "msnbc", "nbc news", "abc news"],
            "priority": 7
        },
        "adult": {
            "keywords": ["adult", "xxx", "18+", "explicit", "mature"],
            "priority": -100  # Lower if not enabled
        },
        "international": {
            "keywords": ["latino", "spanish", "arabic", "hindi", "portuguese", "chinese"],
            "priority": 2
        },
        "entertainment": {
            "keywords": ["entertainment", "reality", "show", "talk"],
            "priority": 3
        }
    }
    
    def __init__(self, channels: list[dict], preferences: dict | None = None) -> None:
        super().__init__()
        self.channels = channels
        self.preferences = preferences or {}
        self.setTerminationEnabled(True)
    
    def run(self) -> None:
        """Execute analysis in background thread."""
        try:
            self.progress.emit("🤖 Initializing AI analyzer...", 5)
            
            # Create result structure
            result = self._create_category_structure()
            
            # Build preference rules
            self.progress.emit("🧠 Learning from preferences...", 15)
            pref_rules = self._build_preference_rules()
            
            # Analyze channels
            self.progress.emit("🔍 Analyzing content...", 30)
            stats = {"total": len(self.channels), "processed": 0, "scored": 0}
            
            for idx, channel in enumerate(self.channels):
                if self.isInterruptionRequested():
                    logger.info("Analysis interrupted")
                    return
                
                if idx % max(1, len(self.channels) // 10) == 0:
                    progress = 30 + int((idx / len(self.channels)) * 60)
                    self.progress.emit(f"Processing {idx}/{len(self.channels)}...", progress)
                
                # Categorize and score
                category, score = self._categorize_and_score(channel, pref_rules)
                
                # Add to results
                if category not in result:
                    result[category] = {"items": [], "groups": {}}
                
                result[category]["items"].append(channel)
                group = channel.get("group", "Uncategorized")
                result[category]["groups"].setdefault(group, []).append(channel)
                
                stats["processed"] += 1
                if score > 0:
                    stats["scored"] += 1
            
            # Sort each category
            for category in result:
                result[category]["items"].sort(
                    key=lambda x: (x.get("_score", 0), x.get("name", "")),
                    reverse=True
                )
            
            # Emit stats
            self.progress.emit(
                f"✨ Analysis complete! {stats['scored']} items prioritized",
                100
            )
            
            result["_stats"] = stats
            event_bus = core.get_event_bus()
            if event_bus is not None:
                event_bus.emit(CHANNELS_LOADED_EVENT, result)
            self.finished.emit(result)
        
        except Exception as e:
            logger.error(f"Analysis error: {e}", exc_info=True)
            event_bus = core.get_event_bus()
            if event_bus is not None:
                event_bus.emit(ERROR_OCCURRED_EVENT, str(e))
            self.finished.emit({"error": str(e)})
    
    def _create_category_structure(self) -> dict:
        """Create empty category structure."""
        return {cat: {"items": [], "groups": {}} 
                for cat in list(self.CATEGORY_RULES.keys()) + ["other"]}
    
    def _build_preference_rules(self) -> dict:
        """Build categorization rules from preferences."""
        def normalize(items):
            return [str(s).lower().strip() for s in (items or [])]
        
        return {
            "series": normalize(self.preferences.get("favorite_series")),
            "directors": normalize(self.preferences.get("favorite_directors")),
            "actors": normalize(self.preferences.get("favorite_actors")),
            "channels": normalize(self.preferences.get("favorite_channels")),
            "genres": normalize(self.preferences.get("genres")),
            "cities": normalize(self.preferences.get("cities")),
            "include_adult": bool(self.preferences.get("include_adult", False))
        }
    
    def _categorize_and_score(self, channel: dict, pref_rules: dict) -> tuple[str, int]:
        """Categorize channel and calculate priority score."""
        name = (channel.get("name") or "").lower()
        group = (channel.get("group") or "").lower()
        
        score = 0
        category = "other"
        
        # Check against favorite channels first (highest priority)
        if pref_rules["channels"]:
            for fav_ch in pref_rules["channels"]:
                if fav_ch in name:
                    score += 200  # Favorite channels get huge boost
                    break
        
        # Check favorites (series, directors, actors)
        for _, fav_list, score_boost in [
            ("series", pref_rules["series"], 150),
            ("directors", pref_rules["directors"], 120),
            ("actors", pref_rules["actors"], 120)
        ]:
            if fav_list:
                for fav in fav_list:
                    if fav in name or fav in group:
                        score += score_boost
                        break
        
        # Categorize by rules
        for cat_key, cat_rules in self.CATEGORY_RULES.items():
            keywords = cat_rules.get("keywords", [])
            if any(kw in name or kw in group for kw in keywords):
                category = cat_key
                score += cat_rules.get("priority", 5)
                break
        
        # Filter adult content if not enabled
        if category == "adult" and not pref_rules["include_adult"]:
            score = -1000  # Deprioritize heavily
        
        # Genre matching (lower priority)
        if pref_rules["genres"] and score >= 0:
            for genre in pref_rules["genres"]:
                if genre in name or genre in group:
                    score += 30
                    break
        
        # City-based filtering
        if pref_rules["cities"] and category == "live":
            is_local = any(city in name for city in pref_rules["cities"])
            if not is_local:
                local_keywords = ["local", "regional", "abc", "nbc", "cbs", "fox"]
                if any(kw in name for kw in local_keywords):
                    score -= 50  # Deprioritize non-local channels
        
        channel["_score"] = score
        channel["_category"] = category if score >= 0 else "filtered"
        
        return category if score >= 0 else "filtered", score
