"""Playlist management: editor dialog, wizard, async loader, and favorites.

Consolidates the former ``playlist_editor`` and ``symon_wizard`` modules.
"""

from __future__ import annotations

import logging
from typing import Any

from PyQt6 import QtWidgets, QtCore, QtGui

logger = logging.getLogger(__name__)

# Type aliases
FavoritesByCategory = dict[str, list[str]]
ItemsByCategory = dict[str, list[dict[str, Any]]]
Item = dict[str, Any]


# ---------------------------------------------------------------------------
# Light-weight playlist editor dialog
# ---------------------------------------------------------------------------

class PlaylistEditor(QtWidgets.QDialog):
    """Dialog for editing playlist sources."""

    def __init__(
        self,
        playlists: list[str] | dict[str, Any] | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Playlists")

        if isinstance(playlists, dict):
            self.playlists = list(playlists.keys())
        else:
            self.playlists = list(playlists or [])

        layout = QtWidgets.QVBoxLayout(self)
        self.list = QtWidgets.QListWidget()
        self.list.addItems(self.playlists)

        add_btn = QtWidgets.QPushButton("Add")
        rem_btn = QtWidgets.QPushButton("Remove")
        add_btn.clicked.connect(self._add)
        rem_btn.clicked.connect(self._remove)

        layout.addWidget(self.list)
        layout.addWidget(add_btn)
        layout.addWidget(rem_btn)

    def _add(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Add M3U", "", "Playlists (*.m3u *.m3u8)"
        )
        if path:
            self.playlists.append(path)
            self.list.addItem(path)

    def _remove(self) -> None:
        row = self.list.currentRow()
        if row >= 0:
            self.playlists.pop(row)
            self.list.takeItem(row)

    def get_playlists(self) -> list[str]:
        """Return current list of playlist paths."""
        return self.playlists


# ---------------------------------------------------------------------------
# Inline managers used by PlaylistWizard
# ---------------------------------------------------------------------------

class FavoritesManager:
    """In-memory favorites tracker (non-persistent)."""

    def __init__(self) -> None:
        self.favorites: FavoritesByCategory = {}

    def add(self, category: str, item: str) -> None:
        if category not in self.favorites:
            self.favorites[category] = []
        if item not in self.favorites[category]:
            self.favorites[category].append(item)

    def remove(self, category: str, item: str) -> None:
        if category in self.favorites and item in self.favorites[category]:
            self.favorites[category].remove(item)

    def get(self, category: str) -> list[str]:
        return self.favorites.get(category, [])


class EPGInfoHelper:
    """Simple EPG info lookup."""

    def __init__(self, epg_data: dict[str, Any] | None) -> None:
        self.epg_data = epg_data or {}

    def get_epg(self, channel_name: str) -> str:
        info = self.epg_data.get(channel_name, {})
        if isinstance(info, dict):
            title = info.get("title", "N/A")
            time_ = info.get("time", "N/A")
            return f"{title} @ {time_}"
        return "No EPG data"


class PlaybackHelper:
    """Minimal playback tracker for wizard."""

    def __init__(self) -> None:
        self._current: tuple[str, str] | None = None

    def play(self, category: str, item: str) -> None:
        self._current = (category, item)
        logger.info("Playing %s from %s", item, category)


class ItemEditor:
    """In-place item rename / reorder / group editor."""

    def __init__(self, data: ItemsByCategory) -> None:
        self.data = data

    def rename(self, category: str, idx: int, new_name: str) -> None:
        items = self.data.get(category, [])
        if 0 <= idx < len(items):
            items[idx]["name"] = new_name

    def reorder(self, category: str, from_idx: int, to_idx: int) -> None:
        items = self.data.get(category, [])
        if 0 <= from_idx < len(items) and 0 <= to_idx < len(items):
            items.insert(to_idx, items.pop(from_idx))

    def group(self, category: str, idx: int, group_name: str) -> None:
        items = self.data.get(category, [])
        if 0 <= idx < len(items):
            items[idx]["group"] = group_name


# ---------------------------------------------------------------------------
# Async search / filter loader
# ---------------------------------------------------------------------------

class AsyncLoader(QtCore.QThread):
    """Background thread for filtering items."""

    dataLoaded = QtCore.pyqtSignal(list)

    def __init__(self, items: list[Item], query: str) -> None:
        super().__init__()
        self.items = items
        self.query = query

    def run(self) -> None:
        try:
            filtered = self._filter(self.items, self.query)
        except Exception as exc:
            logger.error("Filter error: %s", exc)
            filtered = []
        self.dataLoaded.emit(filtered)

    @staticmethod
    def _filter(items: list[Item], query: str) -> list[Item]:
        q = query.lower().strip()
        if not q:
            return items
        return [
            item
            for item in items
            if q in item.get("name", "").lower() or q in item.get("title", "").lower()
        ]


# ---------------------------------------------------------------------------
# AI suggestion helper
# ---------------------------------------------------------------------------

class AISuggester:
    """Recommend most-watched items per category."""

    def suggest(
        self, history: dict[str, Any], items: dict[str, list[Item]],
    ) -> dict[str, list[Item]]:
        return {
            cat: sorted(
                items.get(cat, []),
                key=lambda x: history.get(x.get("name", x.get("title", "")), 0),
                reverse=True,
            )[:5]
            for cat in items
        }


# ---------------------------------------------------------------------------
# Auto-sync manager
# ---------------------------------------------------------------------------

class AutoSyncManager(QtCore.QObject):
    """Batch-export and notification helper."""

    syncProgress = QtCore.pyqtSignal(str)
    syncFinished = QtCore.pyqtSignal(str)
    syncError = QtCore.pyqtSignal(str)

    def __init__(
        self, export_funcs: dict[str, Any], parent: QtCore.QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.export_funcs = export_funcs

    def sync_all(
        self,
        favorites: dict[str, Any],
        all_items: dict[str, Any],
        epg_data: dict[str, Any],
    ) -> None:
        try:
            for key, path in [
                ("m3u", "auto_sync/favorites.m3u"),
                ("xmltv", "auto_sync/epg.xml"),
                ("csv", "auto_sync/favorites.csv"),
            ]:
                if key in self.export_funcs:
                    self.syncProgress.emit(f"Syncing {key.upper()}...")
                    if key == "xmltv":
                        self.export_funcs[key](epg_data, path)
                    else:
                        self.export_funcs[key](favorites, all_items, path)
            self.syncFinished.emit("Auto sync complete!")
        except Exception as exc:
            logger.error("Auto sync failed: %s", exc)
            self.syncError.emit(f"Auto sync failed: {exc}")


# ---------------------------------------------------------------------------
# Stub export helpers (for the wizard's auto-sync)
# ---------------------------------------------------------------------------

def _export_m3u(favorites: FavoritesByCategory, items: ItemsByCategory, path: str) -> None:
    logger.info("Exporting M3U to %s", path)


def _export_xmltv(epg_data: dict[str, Any], path: str) -> None:
    logger.info("Exporting XMLTV to %s", path)


def _export_csv(favorites: FavoritesByCategory, items: ItemsByCategory, path: str) -> None:
    logger.info("Exporting CSV to %s", path)


def _export_favorites(favorites: FavoritesByCategory, path: str) -> None:
    logger.info("Exporting favorites to %s", path)


# ---------------------------------------------------------------------------
# PlaylistWizard (the large dialog)
# ---------------------------------------------------------------------------

class PlaylistWizard(QtWidgets.QDialog):
    """Feature-rich playlist management wizard."""

    def __init__(
        self,
        playlist_data: ItemsByCategory,
        epg_data: dict[str, Any] | None = None,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("TiviMate Playlist Wizard")
        self.setMinimumSize(900, 650)
        layout = QtWidgets.QVBoxLayout(self)

        self.tabs = QtWidgets.QTabWidget()
        layout.addWidget(self.tabs)

        self.live_items = playlist_data.get("live", [])
        self.movies_items = playlist_data.get("movies", [])
        self.series_items = playlist_data.get("series", [])

        # Loaders
        self.liveLoader: AsyncLoader | None = None
        self.moviesLoader: AsyncLoader | None = None
        self.seriesLoader: AsyncLoader | None = None

        # Models / views
        self.liveModel = QtGui.QStandardItemModel()
        self.liveView = QtWidgets.QListView()
        self.liveView.setModel(self.liveModel)
        self.liveView.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.MultiSelection)

        self.moviesModel = QtGui.QStandardItemModel()
        self.moviesView = QtWidgets.QListView()
        self.moviesView.setModel(self.moviesModel)
        self.moviesView.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.MultiSelection)

        self.seriesModel = QtGui.QStandardItemModel()
        self.seriesView = QtWidgets.QListView()
        self.seriesView.setModel(self.seriesModel)
        self.seriesView.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.MultiSelection)

        # Managers
        self.favorites = FavoritesManager()
        self.epg = EPGInfoHelper(epg_data)
        self.playback = PlaybackHelper()
        self.editor = ItemEditor({
            "live": self.live_items,
            "movies": self.movies_items,
            "series": self.series_items,
        })

        export_funcs = {
            "m3u": _export_m3u,
            "xmltv": _export_xmltv,
            "csv": _export_csv,
            "json": _export_favorites,
        }

        # -- Tabs --
        for tab_key, label, search_ph, items, view, filter_fn in [
            ("live", "Live TV", "Search Live TV...", self.live_items, self.liveView, self.filter_live),
            ("movies", "Movies", "Search Movies...", self.movies_items, self.moviesView, self.filter_movies),
            ("series", "Series", "Search Series...", self.series_items, self.seriesView, self.filter_series),
        ]:
            tab = QtWidgets.QWidget()
            tl = QtWidgets.QVBoxLayout(tab)
            search = QtWidgets.QLineEdit()
            search.setPlaceholderText(search_ph)
            search.textChanged.connect(filter_fn)
            tl.addWidget(search)
            if tab_key == "live":
                view.clicked.connect(self.show_epg_info)
            tl.addWidget(view)
            self.tabs.addTab(tab, label)
            setattr(self, f"{tab_key}Search", search)
            setattr(self, f"{tab_key}_items", items)

        self.populate_live(self.live_items[:1000])
        self.populate_movies(self.movies_items[:1000])
        self.populate_series(self.series_items[:1000])

        # -- EPG label --
        self.epgLabel = QtWidgets.QLabel("EPG Info will appear here.")
        layout.addWidget(self.epgLabel)

        # -- Buttons --
        btn_layout = QtWidgets.QHBoxLayout()
        for text, slot in [
            ("Add Selected to Favorites", self.add_selected_to_favorites),
            ("Export for TiviMate", self.export_for_tivimate),
            ("Play Selected", self.play_selected),
            ("Rename Selected Channel", self.rename_selected),
            ("Move Selected Up", self.move_selected_up),
            ("Change Group for Selected", self.change_group_selected),
        ]:
            b = QtWidgets.QPushButton(text)
            b.clicked.connect(slot)
            btn_layout.addWidget(b)
        layout.addLayout(btn_layout)

        self.ai = AISuggester()
        self.auto_sync = AutoSyncManager(export_funcs)
        self.auto_sync.syncProgress.connect(self._show_status)
        self.auto_sync.syncFinished.connect(self._show_status)
        self.auto_sync.syncError.connect(self._show_error)

    # -- Populate helpers ----

    def populate_live(self, items: list[Item]) -> None:
        self.liveModel.clear()
        for ch in items:
            self.liveModel.appendRow(
                QtGui.QStandardItem(f"{ch.get('name', 'Unknown')} ({ch.get('group', 'Other')})")
            )

    def populate_movies(self, items: list[Item]) -> None:
        self.moviesModel.clear()
        for m in items:
            self.moviesModel.appendRow(
                QtGui.QStandardItem(f"{m.get('title', 'Unknown')} ({m.get('group', 'Other')})")
            )

    def populate_series(self, items: list[Item]) -> None:
        self.seriesModel.clear()
        for s in items:
            self.seriesModel.appendRow(
                QtGui.QStandardItem(f"{s.get('title', 'Unknown')} ({s.get('group', 'Other')})")
            )

    # -- Async filters ----

    def _start_loader(
        self, attr_name: str, items: list[Item], text: str, populate_fn: Any,
    ) -> None:
        loader = getattr(self, attr_name, None)
        if loader and loader.isRunning():
            loader.quit()
            loader.wait()
        new_loader = AsyncLoader(items, text)
        new_loader.dataLoaded.connect(populate_fn)
        new_loader.start()
        setattr(self, attr_name, new_loader)

    def filter_live(self, text: str) -> None:
        self._start_loader("liveLoader", self.live_items, text, self.populate_live)

    def filter_movies(self, text: str) -> None:
        self._start_loader("moviesLoader", self.movies_items, text, self.populate_movies)

    def filter_series(self, text: str) -> None:
        self._start_loader("seriesLoader", self.series_items, text, self.populate_series)

    # -- Tab introspection ----

    def _current_tab_key(self) -> str:
        idx = self.tabs.currentIndex()
        return ("live", "movies", "series")[idx] if 0 <= idx < 3 else "live"

    def _view_for_tab(self, tab: str) -> QtWidgets.QListView | None:
        return {"live": self.liveView, "movies": self.moviesView, "series": self.seriesView}.get(tab)

    # -- Actions ----

    def add_selected_to_favorites(self) -> None:
        tab_key = self._current_tab_key()
        view = self._view_for_tab(tab_key)
        if not view:
            return
        selected = view.selectedIndexes()
        if not selected:
            QtWidgets.QMessageBox.information(self, "Favorites", "No items selected")
            return
        for idx in selected:
            self.favorites.add(tab_key, str(idx.data()))
        QtWidgets.QMessageBox.information(self, "Favorites", f"Added {len(selected)} items")

    def export_for_tivimate(self) -> None:
        QtWidgets.QMessageBox.information(self, "Export", "Export functionality placeholder")

    def play_selected(self) -> None:
        tab_key = self._current_tab_key()
        view = self._view_for_tab(tab_key)
        if not view:
            return
        for idx in view.selectedIndexes():
            self.playback.play(tab_key, str(idx.data()))

    def rename_selected(self) -> None:
        tab_key = self._current_tab_key()
        view = self._view_for_tab(tab_key)
        items = getattr(self, f"{tab_key}_items", [])
        if not view or not items:
            return
        idx = view.currentIndex().row()
        if idx < 0 or idx >= len(items):
            QtWidgets.QMessageBox.warning(self, "Rename", "No item selected")
            return
        new_name, ok = QtWidgets.QInputDialog.getText(self, "Rename", "New Channel Name:")
        if ok and new_name.strip():
            self.editor.rename(tab_key, idx, new_name)
            self.refresh_tab(tab_key)

    def move_selected_up(self) -> None:
        tab_key = self._current_tab_key()
        view = self._view_for_tab(tab_key)
        if not view:
            return
        idx = view.currentIndex().row()
        if idx > 0:
            self.editor.reorder(tab_key, idx, idx - 1)
            self.refresh_tab(tab_key)

    def change_group_selected(self) -> None:
        tab_key = self._current_tab_key()
        view = self._view_for_tab(tab_key)
        if not view:
            return
        idx = view.currentIndex().row()
        new_group, ok = QtWidgets.QInputDialog.getText(self, "Change Group", "New Group Name:")
        if ok and new_group.strip():
            self.editor.group(tab_key, idx, new_group)
            self.refresh_tab(tab_key)

    def refresh_tab(self, tab: str) -> None:
        if tab == "live":
            self.populate_live(self.live_items[:1000])
        elif tab == "movies":
            self.populate_movies(self.movies_items[:1000])
        elif tab == "series":
            self.populate_series(self.series_items[:1000])

    def show_epg_info(self, index: QtCore.QModelIndex) -> None:
        try:
            name = index.data().split(" (")[0]
            info = self.epg.get_epg(name)
            self.epgLabel.setText(f"EPG: {info}")
        except Exception as exc:
            logger.error("Error showing EPG info: %s", exc)

    def _show_status(self, msg: str) -> None:
        QtWidgets.QMessageBox.information(self, "Status", msg)

    def _show_error(self, msg: str) -> None:
        QtWidgets.QMessageBox.critical(self, "Error", msg)

    def run_auto_sync(self) -> None:
        self.auto_sync.sync_all(
            self.favorites.favorites,
            {"live": self.live_items, "movies": self.movies_items, "series": self.series_items},
            self.epg.epg_data,
        )

    def show_ai_suggestions(self) -> None:
        suggestions = self.ai.suggest({}, {
            "live": self.live_items,
            "movies": self.movies_items,
            "series": self.series_items,
        })
        msg = "\n".join(
            f"{cat}: {', '.join(item.get('name', item.get('title', 'Unknown')) for item in items)}"
            for cat, items in suggestions.items()
        )
        QtWidgets.QMessageBox.information(self, "AI Suggestions", msg or "No suggestions available")
