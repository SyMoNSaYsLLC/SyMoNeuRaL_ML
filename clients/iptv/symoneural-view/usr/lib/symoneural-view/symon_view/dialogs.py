"""Reusable UI dialogs and widgets for SyMoNeuRaL-View.

Includes:
    - TagWidget, IconButton, DragDropListWidget  (utility widgets)
    - PreferencesDialog       (AI personalization preferences)
    - AIPlaylistAnalyzer      (background playlist categoriser)
    - PlaylistSegmentDialog   (interactive playlist manager)
"""

from __future__ import annotations

import logging
from typing import Any

from PyQt6.QtCore import QSize, Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QCursor, QFont
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QCompleter,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Utility widgets
# ---------------------------------------------------------------------------

class TagWidget(QWidget):
    """Removable tag display widget."""

    removed = pyqtSignal(str)

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.text = text
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        label = QLabel(text)
        label.setStyleSheet("color: #f0f0f0; font-size: 11px;")

        remove_btn = QPushButton("\u00d7")
        remove_btn.setFixedSize(20, 20)
        remove_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        remove_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #FF6B6B; border: none;"
            " font-size: 16px; font-weight: bold; padding: 0; }"
            " QPushButton:hover { color: #FF4444; }"
        )
        remove_btn.clicked.connect(lambda: self.removed.emit(self.text))

        layout.addWidget(label)
        layout.addWidget(remove_btn)
        self.setStyleSheet("QWidget { background-color: #0d7377; border-radius: 4px; }")
        self.setMaximumHeight(30)


class IconButton(QPushButton):
    """Category icon button with visual feedback."""

    def __init__(
        self, icon: str, title: str, count: int, color: str, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.color = color

        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(12, 12, 12, 12)

        for text, style in [
            (icon, f"font-size: 32px; color: {color};"),
            (title, "font-weight: bold; font-size: 11px;"),
            (f"{count:,} items", "font-size: 9px; color: #888;"),
        ]:
            lbl = QLabel(text)
            lbl.setStyleSheet(style)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(lbl)

        self.setMinimumSize(QSize(120, 100))
        self.setMaximumSize(QSize(140, 110))
        self._update_style()

    def _update_style(self) -> None:
        if self.isChecked():
            self.setStyleSheet(
                f"QPushButton {{ background-color: #1a1a1a;"
                f" border: 2px solid {self.color}; border-radius: 8px; }}"
                f" QPushButton:hover {{ background-color: #252525; }}"
            )
        else:
            self.setStyleSheet(
                "QPushButton { background-color: #0f0f0f;"
                " border: 2px solid #333; border-radius: 8px; }"
                f" QPushButton:hover {{ background-color: #1a1a1a;"
                f" border-color: {self.color}; }}"
            )

    def setChecked(self, a0: bool) -> None:  # noqa: N802
        super().setChecked(a0)
        self._update_style()


class DragDropListWidget(QListWidget):
    """List widget with infinite-scroll support."""

    scrolledToBottom = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        scrollbar = self.verticalScrollBar()
        if scrollbar:
            scrollbar.valueChanged.connect(self._check_scroll)

    def _check_scroll(self, value: int) -> None:
        scrollbar = self.verticalScrollBar()
        if scrollbar and (max_val := scrollbar.maximum()) > 0 and value >= max_val - 50:
            self.scrolledToBottom.emit()


# ---------------------------------------------------------------------------
# Preferences dialog
# ---------------------------------------------------------------------------

class PreferencesDialog(QDialog):
    """AI personalization preferences collector."""

    GENRES = [
        "Action", "Horror", "Sci-Fi", "Comedy", "Romance", "Drama",
        "Thriller", "Fantasy", "Mystery", "Musical", "Documentary",
        "Family", "War", "Western", "Crime", "Biography",
    ]

    SUGGESTIONS: dict[str, list[str]] = {
        "series": ["Breaking Bad", "Game of Thrones", "The Office", "Friends", "Stranger Things"],
        "directors": ["Christopher Nolan", "Quentin Tarantino", "Martin Scorsese", "Steven Spielberg"],
        "actors": ["Tom Hanks", "Meryl Streep", "Leonardo DiCaprio", "Denzel Washington"],
        "channels": ["ESPN", "HBO", "CNN", "Discovery", "AMC", "FOX", "NBC", "CBS"],
        "cities": ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"],
    }

    BASE_STYLE = """
        QDialog { background-color: #0f0f0f; color: #f0f0f0; }
        QLabel { color: #f0f0f0; }
        QCheckBox { color: #f0f0f0; spacing: 8px; padding: 4px; }
        QCheckBox::indicator {
            width: 18px; height: 18px; border-radius: 4px;
            border: 2px solid #333; background-color: #1a1a1a;
        }
        QCheckBox::indicator:hover { border-color: #0d7377; }
        QCheckBox::indicator:checked { background-color: #0d7377; border-color: #0d7377; }
        QLineEdit {
            background-color: #1a1a1a; color: #f0f0f0; border: 1px solid #333;
            border-radius: 4px; padding: 10px; font-size: 12px;
        }
        QLineEdit:focus { border: 1px solid #0d7377; }
        QPushButton {
            background-color: #0d7377; color: white; border: none;
            padding: 12px 24px; border-radius: 4px; font-weight: bold; font-size: 12px;
        }
        QPushButton:hover { background-color: #14919b; }
        QScrollArea { border: none; background-color: transparent; }
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("SyMoNeuRaL - Personalize Your Experience")
        self.resize(900, 800)
        self.setStyleSheet(self.BASE_STYLE)

        self.preferences: dict[str, Any] | None = {
            "genres": [], "favorite_series": [], "favorite_directors": [],
            "favorite_actors": [], "favorite_channels": [], "cities": [],
            "include_adult": False, "watch_times": [],
        }
        self.tags_layouts: dict[str, QHBoxLayout] = {}
        self.genre_checkboxes: dict[str, QCheckBox] = {}
        self.time_checkboxes: dict[str, QCheckBox] = {}
        self._build_ui()

    # -- UI construction -----------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        self._add_header(layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        scroll_content = QWidget()
        sl = QVBoxLayout(scroll_content)
        sl.setSpacing(28)

        self._add_input_section(sl, "Your Favorite TV Series", "series",
                                "Type series name and press Enter...")
        self._add_separator(sl)
        self._add_input_section(sl, "Favorite Directors", "directors",
                                "e.g., Christopher Nolan, Quentin Tarantino")
        self._add_input_section(sl, "Favorite Actors/Actresses", "actors",
                                "e.g., Tom Hanks, Meryl Streep", top_margin=12)
        self._add_separator(sl)
        self._add_genre_section(sl)
        self._add_separator(sl)
        self._add_input_section(sl, "Favorite Live TV Channels", "channels",
                                "Type channel name and press Enter...")
        self._add_separator(sl)
        self._add_input_section(sl, "Local Channels", "cities",
                                "Enter cities to keep local channels")
        self._add_separator(sl)
        self._add_content_filter_section(sl)
        self._add_separator(sl)
        self._add_watch_habits_section(sl)

        sl.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        self._add_footer_buttons(layout)

    def _add_header(self, layout: QVBoxLayout) -> None:
        title = QLabel("Let's Personalize Your Experience")
        font = QFont()
        font.setPointSize(20)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        subtitle = QLabel("Help our AI learn what you love to watch")
        subtitle.setStyleSheet("color: #888; font-size: 12px; margin-bottom: 10px;")
        layout.addWidget(subtitle)

    def _add_input_section(
        self, layout: QVBoxLayout, title: str, key: str,
        placeholder: str, top_margin: int = 0,
    ) -> None:
        section_title = QLabel(title)
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        section_title.setFont(font)
        if top_margin:
            section_title.setStyleSheet(f"margin-top: {top_margin}px;")
        layout.addWidget(section_title)

        input_field = QLineEdit()
        input_field.setPlaceholderText(placeholder)
        if key in self.SUGGESTIONS:
            completer = QCompleter(self.SUGGESTIONS[key])
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            input_field.setCompleter(completer)
        input_field.returnPressed.connect(lambda k=key, f=input_field: self._add_item(k, f))
        layout.addWidget(input_field)

        tags_widget = QWidget()
        tags_layout = QHBoxLayout(tags_widget)
        tags_layout.setSpacing(8)
        tags_layout.setContentsMargins(0, 8, 0, 0)
        tags_layout.addStretch()
        self.tags_layouts[key] = tags_layout
        layout.addWidget(tags_widget)

    def _add_genre_section(self, layout: QVBoxLayout) -> None:
        title = QLabel("Preferred Genres")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        desc = QLabel("Select genres you enjoy across all content types")
        desc.setStyleSheet("color: #888; font-size: 11px; margin-bottom: 8px;")
        layout.addWidget(desc)

        grid_widget = QWidget()
        grid_layout = QHBoxLayout(grid_widget)
        col1, col2 = QVBoxLayout(), QVBoxLayout()

        for idx, genre in enumerate(self.GENRES):
            cb = QCheckBox(genre)
            cb.setStyleSheet("font-size: 11px;")
            self.genre_checkboxes[genre] = cb
            (col1 if idx < len(self.GENRES) // 2 else col2).addWidget(cb)

        grid_layout.addLayout(col1)
        grid_layout.addLayout(col2)
        grid_layout.addStretch()
        layout.addWidget(grid_widget)

        btn_layout = QHBoxLayout()
        for text, method, style in [
            ("Select All", self._select_all_genres, ""),
            ("Clear All", self._clear_all_genres,
             "QPushButton { background-color: #333; } QPushButton:hover { background-color: #444; }"),
        ]:
            btn = QPushButton(text)
            btn.clicked.connect(method)
            btn.setMaximumWidth(120)
            if style:
                btn.setStyleSheet(style)
            btn_layout.addWidget(btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _add_content_filter_section(self, layout: QVBoxLayout) -> None:
        title = QLabel("Content Filtering")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        self.adult_checkbox = QCheckBox("Include adult content channels (18+ content)")
        self.adult_checkbox.setStyleSheet("font-size: 12px; color: #FF6B6B;")
        layout.addWidget(self.adult_checkbox)

    def _add_watch_habits_section(self, layout: QVBoxLayout) -> None:
        title = QLabel("Viewing Habits")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        for label, key in [
            ("Morning (6 AM - 12 PM)", "morning"),
            ("Afternoon (12 PM - 6 PM)", "afternoon"),
            ("Evening (6 PM - 10 PM)", "evening"),
            ("Late Night (10 PM - 2 AM)", "night"),
        ]:
            cb = QCheckBox(label)
            cb.setStyleSheet("font-size: 11px;")
            self.time_checkboxes[key] = cb
            layout.addWidget(cb)

    def _add_separator(self, layout: QVBoxLayout) -> None:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: #333;")
        sep.setMaximumHeight(2)
        layout.addWidget(sep)

    def _add_footer_buttons(self, layout: QVBoxLayout) -> None:
        btn_layout = QHBoxLayout()

        skip_btn = QPushButton("Skip (Load Everything)")
        skip_btn.setStyleSheet(
            "QPushButton { background-color: #333; } QPushButton:hover { background-color: #444; }"
        )
        skip_btn.clicked.connect(self._skip_preferences)

        continue_btn = QPushButton("Apply AI Personalization")
        continue_btn.clicked.connect(self._save_preferences)

        btn_layout.addWidget(skip_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(continue_btn)
        layout.addLayout(btn_layout)

    # -- Actions -------------------------------------------------------------

    def _add_item(self, key: str, input_field: QLineEdit) -> None:
        text = input_field.text().strip()
        pref_key = f"favorite_{key}" if key in ("series", "directors", "actors", "channels") else key

        if self.preferences and text and text not in self.preferences[pref_key]:
            self.preferences[pref_key].append(text)
            tag = TagWidget(text)
            tag.removed.connect(lambda t, k=pref_key: self._remove_tag(t, k))
            self.tags_layouts[key].insertWidget(self.tags_layouts[key].count() - 1, tag)
            input_field.clear()

    def _remove_tag(self, text: str, pref_key: str) -> None:
        if self.preferences and text in self.preferences[pref_key]:
            self.preferences[pref_key].remove(text)

    def _select_all_genres(self) -> None:
        for cb in self.genre_checkboxes.values():
            cb.setChecked(True)

    def _clear_all_genres(self) -> None:
        for cb in self.genre_checkboxes.values():
            cb.setChecked(False)

    def _skip_preferences(self) -> None:
        self.preferences = None
        self.accept()

    def _save_preferences(self) -> None:
        genres = [genre.lower() for genre, cb in self.genre_checkboxes.items() if cb.isChecked()]
        watch_times = [key for key, cb in self.time_checkboxes.items() if cb.isChecked()]

        if self.preferences:
            self.preferences.update({
                "genres": genres,
                "include_adult": self.adult_checkbox.isChecked(),
                "watch_times": watch_times,
            })
        self.accept()

    def get_preferences(self) -> dict[str, Any] | None:
        """Return collected preferences, or *None* if skipped."""
        return self.preferences


# ---------------------------------------------------------------------------
# AI playlist analyser (runs in background thread)
# ---------------------------------------------------------------------------

class AIPlaylistAnalyzer(QThread):
    """AI-powered playlist analyzer with intelligent categorization."""

    progress = pyqtSignal(str, int)
    finished = pyqtSignal(dict)

    CATEGORIES: dict[str, dict[str, Any]] = {
        "kids": {"keywords": ["kids", "cartoon", "disney", "nick"]},
        "news": {"keywords": ["news", "cnn", "msnbc", "bbc news"]},
        "sports": {"keywords": ["sport", "espn", "nba", "nfl"]},
        "entertainment": {"keywords": ["entertainment", "reality"]},
        "international": {"keywords": ["latino", "spanish", "arabic"]},
        "adult": {"keywords": ["adult", "xxx", "18+", "explicit"]},
    }

    def __init__(
        self,
        channels: list[dict[str, Any]],
        epg_guide: dict[str, Any],
        preferences: dict[str, Any] | None = None,
    ) -> None:
        super().__init__()
        self.channels = channels
        self.epg_guide = epg_guide
        self.preferences = preferences or {}

    def run(self) -> None:
        try:
            self.progress.emit("Analyzing playlist with your preferences...", 10)

            result: dict[str, dict[str, Any]] = {
                cat: {"items": [], "groups": {}}
                for cat in [
                    "live", "movies", "series", "sports", "kids", "news",
                    "entertainment", "adult", "international", "other",
                ]
            }

            prefs = self._extract_preferences()
            self.progress.emit("Applying AI filters and categorizing...", 30)

            stats = {"filtered": 0, "prioritized": 0}
            total = len(self.channels)

            for idx, ch in enumerate(self.channels):
                if idx % 100 == 0:
                    pct = 30 + int((idx / max(total, 1)) * 40)
                    self.progress.emit(
                        f"Processing {idx}/{total}... ({stats['prioritized']} favorites)", pct,
                    )

                name = (ch.get("name") or "").lower()
                group = (ch.get("group") or "").lower()
                has_url = bool(ch.get("url"))

                if not has_url and "series" not in group:
                    stats["filtered"] += 1
                    continue

                ch["_score"], ch["_priority"] = self._calculate_priority(name, group, prefs)
                if ch["_score"] > 0:
                    stats["prioritized"] += 1

                if self._should_filter(name, group, prefs):
                    stats["filtered"] += 1
                    continue

                category = self._categorize_channel(name, group, has_url)

                result[category]["items"].append(ch)
                group_key = ch.get("group", "Uncategorized")
                result[category]["groups"].setdefault(group_key, []).append(ch)

            for cat in result.values():
                cat["items"].sort(key=lambda x: x.get("_score", 0), reverse=True)

            total_items = sum(len(cat["items"]) for cat in result.values())
            self.progress.emit(
                f"Complete! {total_items:,} items ({stats['prioritized']} favorites)", 100,
            )
            self.finished.emit(result)

        except Exception as exc:
            logger.error("Analysis failed: %s", exc, exc_info=True)
            self.finished.emit({"error": str(exc)})

    # -- helpers --

    def _extract_preferences(self) -> dict[str, Any]:
        return {
            "genres": [g.lower() for g in self.preferences.get("genres", [])],
            "series": [s.lower() for s in self.preferences.get("favorite_series", [])],
            "directors": [d.lower() for d in self.preferences.get("favorite_directors", [])],
            "actors": [a.lower() for a in self.preferences.get("favorite_actors", [])],
            "channels": [c.lower() for c in self.preferences.get("favorite_channels", [])],
            "cities": [c.lower() for c in self.preferences.get("cities", [])],
            "include_adult": self.preferences.get("include_adult", True),
        }

    def _calculate_priority(
        self, name: str, group: str, prefs: dict[str, Any],
    ) -> tuple[int, str]:
        checks = [
            (prefs["series"], 100, "FAVORITE SERIES"),
            (prefs["directors"], 80, "FAVORITE DIRECTOR"),
            (prefs["actors"], 80, "FAVORITE ACTOR"),
            (prefs["channels"], 90, "FAVORITE CHANNEL"),
        ]
        for items, score, label in checks:
            if items and any(item in name or item in group for item in items):
                return score, label
        return 0, ""

    def _should_filter(self, name: str, group: str, prefs: dict[str, Any]) -> bool:
        if prefs["cities"]:
            local_kw = ["local", "abc", "nbc", "cbs", "fox", "pbs"]
            if any(kw in name for kw in local_kw):
                if not any(city in name for city in prefs["cities"]):
                    return True

        is_adult = any(
            kw in name or kw in group for kw in self.CATEGORIES["adult"]["keywords"]
        )
        if is_adult and not prefs["include_adult"]:
            return True

        if prefs["genres"] and ("series" in group or "vod" in group or "movie" in group):
            if not any(genre in name or genre in group for genre in prefs["genres"]):
                return True

        return False

    def _categorize_channel(self, name: str, group: str, has_url: bool) -> str:
        for cat_key, cat_data in self.CATEGORIES.items():
            if any(kw in name or kw in group for kw in cat_data["keywords"]):
                return cat_key
        if "series" in group or not has_url:
            return "series"
        if any(kw in group for kw in ("vod", "movie", "film")):
            return "movies"
        return "live"


# ---------------------------------------------------------------------------
# Playlist segment dialog
# ---------------------------------------------------------------------------

class PlaylistSegmentDialog(QDialog):
    """Interactive playlist manager with AI categorization."""

    CATEGORIES = [
        ("Live TV", "live", "#FF6B6B"),
        ("Movies", "movies", "#4ECDC4"),
        ("Series", "series", "#45B7D1"),
        ("Sports", "sports", "#FFA502"),
        ("Kids", "kids", "#FF6BC5"),
        ("News", "news", "#FFC107"),
        ("Entertainment", "entertainment", "#9C27B0"),
        ("International", "international", "#00BCD4"),
        ("Adult", "adult", "#C0392B"),
        ("Other", "other", "#95A5A6"),
    ]

    BASE_STYLE = """
        QDialog { background-color: #0f0f0f; color: #f0f0f0; }
        QLabel { color: #f0f0f0; }
        QLineEdit {
            background-color: #1a1a1a; color: #f0f0f0; border: 1px solid #333;
            border-radius: 4px; padding: 8px; font-size: 11px;
        }
        QLineEdit:focus { border: 1px solid #0d7377; }
        DragDropListWidget {
            background-color: #1a1a1a; color: #f0f0f0; border: 1px solid #333;
            border-radius: 4px; outline: none;
        }
        QListWidget::item { padding: 8px 10px; border-bottom: 1px solid #222; }
        QListWidget::item:hover { background-color: #252525; }
        QListWidget::item:selected {
            background-color: #0d7377; border-left: 3px solid #14919b;
        }
        QScrollBar:vertical { background-color: #1a1a1a; width: 10px; border-radius: 5px; }
        QScrollBar::handle:vertical { background-color: #404040; border-radius: 5px; }
        QScrollBar::handle:vertical:hover { background-color: #555; }
        QPushButton {
            background-color: #0d7377; color: white; border: none;
            padding: 12px 24px; border-radius: 4px; font-weight: bold; font-size: 12px;
        }
        QPushButton:hover { background-color: #14919b; }
    """

    def __init__(
        self,
        channels: list[dict[str, Any]],
        epg_guide: dict[str, Any],
        preferences: dict[str, Any] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("SyMoNeuRaL - Intelligent Playlist Manager")
        self.resize(1600, 900)
        self.setStyleSheet(self.BASE_STYLE)

        self.channels = channels
        self.epg_guide = epg_guide
        self.preferences = preferences
        self.segmented_data: dict[str, Any] = {}
        self.current_category: str | None = None
        self.category_buttons: dict[str, IconButton] = {}

        self._init_ui()
        self._start_analysis()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("AI-Personalized Playlist Manager")
        font = QFont()
        font.setPointSize(18)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        subtitle = QLabel(self._build_subtitle())
        subtitle.setStyleSheet("color: #888; font-size: 11px; margin-bottom: 8px;")
        layout.addWidget(subtitle)

        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(
            "QProgressBar { border: 1px solid #333; border-radius: 4px;"
            " text-align: center; color: #f0f0f0; height: 26px; }"
            " QProgressBar::chunk { background-color: #0d7377; border-radius: 3px; }"
        )
        self.progress_bar.setMaximum(100)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Initializing AI personalization...")
        self.status_label.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(self.status_label)

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(12)
        self.content_widget.setVisible(False)
        layout.addWidget(self.content_widget)

        btn_layout = QHBoxLayout()
        self.continue_btn = QPushButton("Continue to Media Player")
        self.continue_btn.setEnabled(False)
        self.continue_btn.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(self.continue_btn)
        layout.addLayout(btn_layout)

    def _build_subtitle(self) -> str:
        if not self.preferences:
            return "AI-powered organization - Smart grouping - Progressive loading"
        parts: list[str] = []
        for key, label in [
            ("favorite_series", "series"), ("favorite_directors", "directors"),
            ("favorite_actors", "actors"), ("favorite_channels", "channels"),
            ("genres", "genres"),
        ]:
            if items := self.preferences.get(key):
                parts.append(f"{len(items)} {label}")
        return f"Personalized: {' | '.join(parts)}" if parts else "AI-powered organization"

    def _start_analysis(self) -> None:
        self.analyzer = AIPlaylistAnalyzer(self.channels, self.epg_guide, self.preferences)
        self.analyzer.progress.connect(self._on_progress)
        self.analyzer.finished.connect(self._on_analysis_complete)
        self.analyzer.start()

    def _on_progress(self, msg: str, value: int) -> None:
        self.status_label.setText(msg)
        self.progress_bar.setValue(value)

    def _on_analysis_complete(self, result: dict[str, Any]) -> None:
        if "error" in result:
            QMessageBox.critical(self, "Error", f"Analysis failed: {result['error']}")
            self.reject()
            return
        self.segmented_data = result
        QTimer.singleShot(200, self._build_category_view)

    def _build_category_view(self) -> None:
        self.progress_bar.setValue(100)
        self.status_label.setText("Your personalized content is ready! Select a category.")
        self.content_widget.setVisible(True)

        cat_title = QLabel("Your Content Categories")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        cat_title.setFont(font)
        self.content_layout.addWidget(cat_title)

        grid_widget = QWidget()
        grid_layout = QHBoxLayout(grid_widget)
        grid_layout.setSpacing(12)

        for title, key, color in self.CATEGORIES:
            count = len(self.segmented_data.get(key, {}).get("items", []))
            if count == 0:
                continue
            btn = IconButton(title[0], title, count, color)
            btn.clicked.connect(lambda checked=False, k=key: self._on_category_selected(k))
            grid_layout.addWidget(btn)
            self.category_buttons[key] = btn

        grid_layout.addStretch()
        self.content_layout.addWidget(grid_widget)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: #333;")
        sep.setMaximumHeight(2)
        self.content_layout.addWidget(sep)

        self.detail_layout = QHBoxLayout()
        self.detail_layout.setSpacing(16)
        self.content_layout.addLayout(self.detail_layout)

        self.continue_btn.setEnabled(True)

    def _on_category_selected(self, category_key: str) -> None:
        for key, btn in self.category_buttons.items():
            btn.setChecked(key == category_key)
        self.current_category = category_key
        self._build_detail_view()

    def _build_detail_view(self) -> None:
        while self.detail_layout.count():
            item = self.detail_layout.takeAt(0)
            if item and (widget := item.widget()):
                widget.deleteLater()

        if self.current_category is None:
            return
        category_data = self.segmented_data[self.current_category]

        # Left: groups
        self._add_group_panel(category_data)
        # Middle: items
        self._add_items_panel()
        # Right: preview
        self._add_preview_panel()

        self.group_list.setCurrentRow(0)
        if current := self.group_list.currentItem():
            self._on_group_selected(current)

    def _add_group_panel(self, category_data: dict[str, Any]) -> None:
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setSpacing(8)
        ll.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Smart Groups")
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        title.setFont(font)
        ll.addWidget(title)

        self.group_list = QListWidget()
        self.group_list.setMaximumWidth(280)
        self.group_list.setMinimumWidth(250)

        all_item = QListWidgetItem(f"All Items ({len(category_data['items'])})")
        all_item.setData(Qt.ItemDataRole.UserRole, "__all__")
        self.group_list.addItem(all_item)

        sorted_groups = sorted(
            category_data["groups"].items(), key=lambda x: len(x[1]), reverse=True,
        )
        for group_name, group_items in sorted_groups:
            if len(group_items) < 3:
                continue
            item = QListWidgetItem(f"{group_name} ({len(group_items)})")
            item.setData(Qt.ItemDataRole.UserRole, group_name)
            self.group_list.addItem(item)

        self.group_list.itemClicked.connect(self._on_group_selected)
        ll.addWidget(self.group_list)
        left.setMaximumWidth(300)
        self.detail_layout.addWidget(left)

    def _add_items_panel(self) -> None:
        mid = QWidget()
        ml = QVBoxLayout(mid)
        ml.setSpacing(8)
        ml.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Content")
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        title.setFont(font)
        ml.addWidget(title)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search content...")
        self.search_box.textChanged.connect(self._on_search)
        ml.addWidget(self.search_box)

        self.item_list = DragDropListWidget()
        self.item_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.item_list.itemClicked.connect(self._on_item_clicked)
        ml.addWidget(self.item_list)

        self.detail_layout.addWidget(mid, 1)

    def _add_preview_panel(self) -> None:
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setSpacing(10)

        title = QLabel("Preview")
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        title.setFont(font)
        rl.addWidget(title)

        self.cover_image = QLabel("Select an item\nto preview")
        self.cover_image.setFixedSize(QSize(260, 390))
        self.cover_image.setStyleSheet(
            "border: 2px solid #0d7377; border-radius: 8px;"
            " background-color: #1a1a1a; color: #666;"
        )
        self.cover_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rl.addWidget(self.cover_image)

        self.cover_title = QLabel("\u2014")
        font2 = QFont()
        font2.setPointSize(11)
        font2.setBold(True)
        self.cover_title.setFont(font2)
        self.cover_title.setWordWrap(True)
        self.cover_title.setMaximumWidth(260)
        rl.addWidget(self.cover_title)

        self.cover_group = QLabel("\u2014")
        self.cover_group.setStyleSheet("font-size: 10px; color: #888;")
        rl.addWidget(self.cover_group)

        self.cover_priority = QLabel("")
        self.cover_priority.setStyleSheet("font-size: 10px; color: #0d7377; font-weight: bold;")
        rl.addWidget(self.cover_priority)

        rl.addStretch()
        right.setMaximumWidth(280)
        self.detail_layout.addWidget(right)

    # -- interaction ---------------------------------------------------------

    def _on_group_selected(self, item: QListWidgetItem) -> None:
        group_name = item.data(Qt.ItemDataRole.UserRole)
        if self.current_category is None:
            return
        cat = self.segmented_data[self.current_category]

        items = cat["items"] if group_name == "__all__" else cat["groups"].get(group_name, [])
        self.item_list.clear()
        for ch in items:
            display = ch.get("name", "Unknown")
            if priority := ch.get("_priority"):
                display = f"{priority} - {display}"
            li = QListWidgetItem(display)
            li.setData(Qt.ItemDataRole.UserRole, ch)
            self.item_list.addItem(li)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        ch = item.data(Qt.ItemDataRole.UserRole)
        if not ch:
            return
        self.cover_title.setText(ch.get("name", "Unknown"))
        self.cover_group.setText(f"Group: {ch.get('group', 'N/A')}")
        self.cover_priority.setText(ch.get("_priority", ""))

    def _on_search(self, text: str) -> None:
        query = text.lower()
        for i in range(self.item_list.count()):
            item = self.item_list.item(i)
            if item:
                item.setHidden(query not in item.text().lower())
