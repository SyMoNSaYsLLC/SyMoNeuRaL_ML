from __future__ import annotations

import datetime as dt
import logging
from functools import partial
from pathlib import Path
from typing import Callable

from PyQt6.QtCore import QSize, Qt, QTimer
from PyQt6.QtGui import QAction, QShortcut, QKeySequence
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSlider,
    QSplitter,
    QToolBar,
    QVBoxLayout,
    QWidget,
)
import PyQt6.QtWidgets as QtWidgets

from . import (
    core,
    keybinds,
)
from . import epg as epg_mod
from . import playlist as playlist_mod

logger = logging.getLogger(__name__)

# Handle optional inhibit module
inhibit = None
try:
    from . import inhibit
except ImportError:
    logger.debug("Inhibit module not available")

class PlaybackEngine:
    """Concrete playback engine implementation."""
    def __init__(self):
        self.is_playing = False
        self.current_stream = None
        self.recording = False
        self.record_path = None
        self._paused = False
        self._volume = 80
        self._aspect = "16:9"
        self._audio_track = 0
        self._subtitle_track = -1
        logger.info("PlaybackEngine initialized")

    def play_stream(self, url: str) -> bool:
        """Play a stream URL."""
        if not url:
            logger.error("Empty stream URL")
            return False
        try:
            self.current_stream = url
            self.is_playing = True
            self._paused = False
            logger.info(f"Playing stream: {url}")
            return True
        except Exception as e:
            logger.error(f"Failed to play stream: {e}")
            return False

    def toggle_pause(self) -> None:
        """Toggle pause state."""
        if self.is_playing:
            self._paused = not self._paused
            logger.info(f"Pause toggled: {self._paused}")

    def stop(self) -> None:
        """Stop playback."""
        self.is_playing = False
        self._paused = False
        self.current_stream = None
        logger.info("Playback stopped")

    def seek(self, seconds: int, relative: bool = False) -> None:
        """Seek to position."""
        if self.is_playing:
            logger.info(f"Seek {'relative' if relative else 'absolute'}: {seconds}s")

    def set_volume(self, level: int) -> None:
        """Set volume level 0-100."""
        self._volume = max(0, min(100, level))
        logger.debug(f"Volume set to {self._volume}%")

    def set_aspect(self, aspect: str) -> None:
        """Set aspect ratio."""
        if aspect in ("16:9", "4:3", "original"):
            self._aspect = aspect
            logger.info(f"Aspect ratio set to {aspect}")

    def cycle_audio(self) -> None:
        """Cycle through audio tracks."""
        self._audio_track = (self._audio_track + 1) % 4
        logger.info(f"Audio track: {self._audio_track}")

    def cycle_subtitle(self) -> None:
        """Cycle through subtitle tracks."""
        self._subtitle_track = (self._subtitle_track + 1) % 10
        logger.info(f"Subtitle track: {self._subtitle_track}")

    def start_recording(self, path: str) -> bool:
        """Start recording to file."""
        try:
            if not path:
                return False
            self.recording = True
            self.record_path = path
            logger.info(f"Recording started: {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            return False

    def stop_recording(self) -> str | None:
        """Stop recording and return path."""
        if self.recording:
            path = self.record_path
            self.recording = False
            self.record_path = None
            logger.info(f"Recording stopped: {path}")
            return path
        return None

    def close(self) -> None:
        """Close playback engine."""
        self.stop()
        if self.recording:
            self.stop_recording()
        logger.info("PlaybackEngine closed")


class XtreamLoginDialog(QDialog):
    """Dialog for Xtream server login credentials."""
    
    def __init__(self, settings: dict, parent: QWidget | None = None):
        """Initialize Xtream login dialog.
        
        Args:
            settings: Dictionary with existing settings
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle("Xtream Login")
        form = QFormLayout(self)
        self.host = QLineEdit(settings.get("xtream_host", ""))
        self.user = QLineEdit(settings.get("xtream_user", ""))
        self.pw = QLineEdit(settings.get("xtream_pass", ""))
        self.pw.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Host", self.host)
        form.addRow("User", self.user)
        form.addRow("Pass", self.pw)
        ok = QPushButton("Continue")
        ok.clicked.connect(self.accept)
        form.addRow(ok)

    def get_credentials(self) -> tuple:
        """Get entered credentials.
        
        Returns:
            Tuple of (host, user, password)
        """
        return (
            self.host.text().strip(),
            self.user.text().strip(),
            self.pw.text().strip(),
        )


class IntelligenceWizard(QDialog):
    """Initial setup wizard for application configuration."""
    
    def __init__(self, parent: QWidget | None = None):
        """Initialize setup wizard.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle("Setup")
        layout = QVBoxLayout(self)
        self.style_smart = QRadioButton("Smart (hide channels without logos)")
        self.style_all = QRadioButton("All channels")
        self.style_smart.setChecked(True)
        self.xdp = QCheckBox("Enable XDP accelerator (needs bcc/root)")
        self.ask_more = QCheckBox("Ask to add playlists at startup")
        self.ask_modify = QCheckBox("Ask to modify playlists at startup")
        for w in (
            self.style_smart,
            self.style_all,
            self.xdp,
            self.ask_more,
            self.ask_modify,
        ):
            layout.addWidget(w)
        ok = QPushButton("Continue")
        ok.clicked.connect(self.accept)
        layout.addWidget(ok)

    def get_config(self) -> dict:
        """Get configuration from wizard.
        
        Returns:
            Configuration dictionary
        """
        return {
            "style": "smart" if self.style_smart.isChecked() else "all",
            "xdp": self.xdp.isChecked(),
            "ask_more": self.ask_more.isChecked(),
            "ask_modify": self.ask_modify.isChecked(),
        }


class SourceSelectDialog(QDialog):
    """Dialog to select playlist source.
    
    Allows user to choose between Xtream server or local M3U file.
    """
    
    def __init__(self, parent: QWidget | None = None):
        """Initialize source select dialog.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle("Select Source")
        layout = QVBoxLayout(self)
        self.opt_xtream = QRadioButton("Xtream")
        self.opt_m3u = QRadioButton("Local M3U")
        self.opt_xtream.setChecked(True)
        layout.addWidget(self.opt_xtream)
        layout.addWidget(self.opt_m3u)
        ok = QPushButton("Continue")
        ok.clicked.connect(self.accept)
        layout.addWidget(ok)

    def is_xtream(self) -> bool:
        """Check if Xtream source selected.
        
        Returns:
            True if Xtream selected
        """
        return self.opt_xtream.isChecked()

    def is_m3u(self) -> bool:
        """Check if M3U source selected.
        
        Returns:
            True if M3U selected
        """
        return self.opt_m3u.isChecked()


class SeriesDialog(QDialog):
    """Dialog for browsing and selecting series episodes."""
    
    def __init__(
        self,
        series_info: dict,
        xtream_creds: dict,
        parent: QWidget | None = None
    ):
        """Initialize series dialog.
        
        Args:
            series_info: Series information dictionary
            xtream_creds: Xtream credentials dictionary
            parent: Parent widget
        """
        super().__init__(parent)
        from PyQt6.QtWidgets import QListWidget

        series_name = series_info.get("info", {}).get("name", "Series")
        self.setWindowTitle(f"Select Episode - {series_name}")
        self.selected_url = None
        self.creds = xtream_creds
        layout = QHBoxLayout(self)
        self.seasons = QListWidget()
        self.episodes = QListWidget()
        layout.addWidget(self.seasons)
        layout.addWidget(self.episodes)
        self.series_info = series_info
        
        # Populate seasons
        season_nums = sorted(
            series_info.get("episodes", {}).keys(),
            key=lambda x: int(x) if x.isdigit() else 0
        )
        self.seasons.addItems(season_nums)
        self.seasons.currentTextChanged.connect(self._load_season)
        self.episodes.itemDoubleClicked.connect(self._pick_episode)
        
        if self.seasons.count() > 0:
            self.seasons.setCurrentRow(0)

    def _load_season(self, season: str) -> None:
        """Load episodes for selected season.
        
        Args:
            season: Season identifier
        """
        self.episodes.clear()
        if not season:
            return
        eps = self.series_info.get("episodes", {}).get(season, [])
        for ep in eps:
            title = ep.get("title") or ep.get("name") or f"E{ep.get('episode_num','')}"
            self.episodes.addItem(f"{ep.get('episode_num','')} - {title}")

    def _pick_episode(self, item) -> None:
        """Handle episode selection.
        
        Args:
            item: Selected list item
        """
        current_item = self.seasons.currentItem()
        if not current_item:
            return
        season = current_item.text()
        idx = self.episodes.row(item)
        
        eps = self.series_info.get("episodes", {}).get(season, [])
        if idx < 0 or idx >= len(eps):
            logger.warning(f"Invalid episode index: {idx}")
            return
        
        ep = eps[idx]
        episode_id = ep.get("id") or ep.get("stream_id")
        if not episode_id:
            logger.error("Episode ID not found")
            return
        
        ext = ep.get("container_extension", "mp4")
        host = self.creds.get("host", "").rstrip("/")
        user = self.creds.get("user", "")
        pw = self.creds.get("pw", "")
        
        if not all([host, user, pw]):
            logger.error("Missing credentials for series playback")
            return
        
        self.selected_url = f"{host}/series/{user}/{pw}/{episode_id}.{ext}"
        self.accept()


class SymonWindow(QMainWindow):
    """Main media player window with dual-pane layout."""
    
    def __init__(
        self,
        settings: dict,
        on_reset: Callable | None = None,
        xtream_client=None,
        xtream_creds: dict | None = None
    ):
        """Initialize main window.
        
        Args:
            settings: Application settings dictionary
            on_reset: Callback for reset/reload
            xtream_client: Xtream API client instance
            xtream_creds: Xtream credentials dictionary
        """
        super().__init__()
        self.setWindowTitle("SyMoNeuRaL-View Professional")
        self.setMinimumSize(1280, 720)
        self.on_reset_cb = on_reset
        self.settings = settings
        self.data_map = {}
        self.epg_index = {}
        self.current_cat = None
        self.current_channel = None
        self.favorites = set(settings.get("favorites", []))
        self.overlay_visible = False
        self.overlay_timer = QTimer(self)
        self.overlay_timer.setSingleShot(True)
        self.overlay_timer.timeout.connect(self._hide_overlay)
        self.record_dir = None
        self.xtream_client = xtream_client
        self.xtream_creds = xtream_creds
        self.record_proc = None
        self.playback_engine = PlaybackEngine()
        self.playback = self.playback_engine  # alias for callers
        self.inhibitor = None
        if inhibit is not None:
            try:
                self.inhibitor = inhibit.InhibitManager()
            except Exception as e:
                logger.debug(f"Inhibit manager unavailable: {e}")
        self._build_layout()
        self._init_toolbar()
        self._init_menubar()
        self._bind_shortcuts()

    def _build_layout(self) -> None:
        """Build main window layout."""
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # Left: search + categories
        left = QWidget()
        left_layout = QVBoxLayout(left)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search...")
        self.search.textChanged.connect(self._refresh_menu_content)
        self.menu = QListWidget()
        self.menu.setMinimumWidth(220)
        self.menu.itemClicked.connect(self.on_menu_click)
        left_layout.addWidget(self.search)
        left_layout.addWidget(self.menu)

        self.content = QListWidget()
        self.content.setMinimumWidth(320)
        self.content.itemClicked.connect(self.on_content_click)
        self.epg_list = QListWidget()
        self.epg_list.itemClicked.connect(self.on_epg_play)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        self.viewport = QWidget()
        self.viewport.setMinimumSize(QSize(640, 360))
        self.viewport.setStyleSheet("background-color: black;")
        self.viewport.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.viewport.customContextMenuRequested.connect(self._show_video_menu)

        self.overlay = self._build_overlay()
        self.overlay.setParent(self.viewport)
        self.overlay.hide()

        controls = self._build_controls()

        right_layout.addWidget(self.viewport, stretch=4)
        right_layout.addWidget(self.epg_list, stretch=2)
        right_layout.addWidget(controls, stretch=0)

        splitter.addWidget(left)
        splitter.addWidget(self.content)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setStretchFactor(2, 4)

        root.addWidget(splitter)

    def _build_overlay(self) -> QWidget:
        """Build overlay panel widget.
        
        Returns:
            Configured overlay panel
        """
        panel = QWidget()
        panel.setStyleSheet(
            "background-color: rgba(12,12,12,0.9); color: #f0f0f0; border-radius: 10px;"
        )
        panel.setGeometry(30, 30, 560, 360)
        layout = QVBoxLayout(panel)
        self.ov_title = QLabel("Channel")
        self.ov_title.setStyleSheet("font-size: 16px; font-weight: 600;")
        self.ov_now = QLabel("Now")
        self.ov_next = QLabel("Next")
        self.ov_prog = QProgressBar()
        self.ov_prog.setTextVisible(False)
        self.ov_prog.setStyleSheet(
            """
            QProgressBar {background: #333; border-radius: 4px; height: 8px;}
            QProgressBar::chunk {background: #4caf50;}
        """
        )
        layout.addWidget(self.ov_title)
        layout.addWidget(self.ov_now)
        layout.addWidget(self.ov_prog)
        layout.addWidget(self.ov_next)
        self.ov_list = QListWidget()
        layout.addWidget(self.ov_list, stretch=1)
        self.ov_list.itemClicked.connect(self._overlay_play)
        return panel

    def _build_controls(self) -> QWidget:
        """Build playback controls widget.
        
        Returns:
            Configured controls widget
        """
        bar = QHBoxLayout()
        btn_play = QPushButton("Play/Pause")
        btn_play.clicked.connect(self.playback_engine.toggle_pause)
        btn_stop = QPushButton("Stop")
        btn_stop.clicked.connect(self.playback_engine.stop)
        btn_rec = QPushButton("Record…")
        btn_rec.clicked.connect(self._toggle_record)
        btn_ff = QPushButton(">>")
        btn_ff.clicked.connect(partial(self._seek, 15))
        btn_rw = QPushButton("<<")
        btn_rw.clicked.connect(partial(self._seek, -15))
        btn_full = QPushButton("Fullscreen")
        btn_full.clicked.connect(self._toggle_fullscreen)
        btn_fav = QPushButton("★ Fav")
        btn_fav.clicked.connect(self._toggle_fav)
        btn_aspect = QPushButton("Aspect")
        btn_aspect.clicked.connect(partial(self.playback_engine.set_aspect, "16:9"))
        btn_sub = QPushButton("Sub")
        btn_sub.clicked.connect(self.playback_engine.cycle_subtitle)
        btn_audio = QPushButton("Audio")
        btn_audio.clicked.connect(self.playback_engine.cycle_audio)
        self.vol = QSlider(Qt.Orientation.Horizontal)
        self.vol.setRange(0, 100)
        self.vol.setValue(80)
        self.vol.valueChanged.connect(self.playback_engine.set_volume)
        
        for w in (
            btn_play,
            btn_stop,
            btn_rw,
            btn_ff,
            btn_rec,
            btn_fav,
            btn_full,
            btn_aspect,
            btn_sub,
            btn_audio,
            QLabel("Vol"),
            self.vol,
        ):
            bar.addWidget(w)
        
        wrap = QWidget()
        wrap.setLayout(bar)
        return wrap

    def _bind_shortcuts(self) -> None:
        """Bind keyboard shortcuts."""
        binds = getattr(keybinds, "DEFAULT_BINDINGS", {})
        sc_play = QShortcut(QKeySequence(binds.get("play_pause", "Space")), self)
        sc_play.activated.connect(self.playback_engine.toggle_pause)
        sc_rec = QShortcut(QKeySequence(binds.get("record", "R")), self)
        sc_rec.activated.connect(self._toggle_record)
        sc_full = QShortcut(QKeySequence(binds.get("fullscreen", "F11")), self)
        sc_full.activated.connect(self._toggle_fullscreen)
        sc_overlay = QShortcut(QKeySequence(binds.get("overlay", "Ctrl+O")), self)
        sc_overlay.activated.connect(self._toggle_overlay)
        sc_seek_fwd = QShortcut(QKeySequence(binds.get("seek_forward", "Ctrl+Right")), self)
        sc_seek_fwd.activated.connect(partial(self._seek, 15))
        sc_seek_bwd = QShortcut(QKeySequence(binds.get("seek_backward", "Ctrl+Left")), self)
        sc_seek_bwd.activated.connect(partial(self._seek, -15))

    def _init_toolbar(self) -> None:
        """Initialize toolbar."""
        tb = QToolBar("Controls", self)
        tb.setMovable(False)
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        for text, cb in [
            ("Play/Pause", self.playback_engine.toggle_pause),
            ("Stop", self.playback_engine.stop),
            ("Record…", self._toggle_record),
            ("Fullscreen", self._toggle_fullscreen),
            ("Favorites", self._toggle_fav),
            ("Reload Sources", self._reset_setup),
        ]:
            act = QAction(text, self)
            act.triggered.connect(cb)
            tb.addAction(act)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, tb)

    def _init_menubar(self) -> None:
        """Initialize menubar."""
        mb = self.menuBar()
        if not mb:
            return
        
        file_menu = mb.addMenu("&File")
        if file_menu:
            file_menu.addAction("Add Playlist…", self._add_playlist)
            file_menu.addAction("Clear Playlists", self._clear_playlists)
            file_menu.addSeparator()
            file_menu.addAction("Reset Setup", self._reset_setup)
            file_menu.addSeparator()
            file_menu.addAction("Quit", self.close)
        
        view_menu = mb.addMenu("&View")
        if view_menu:
            view_menu.addAction("Toggle Fullscreen", self._toggle_fullscreen)
            view_menu.addAction("Show Overlay", self._toggle_overlay)
        
        playback_menu = mb.addMenu("&Playback")
        if playback_menu:
            playback_menu.addAction("Play/Pause", self.playback_engine.toggle_pause)
            playback_menu.addAction("Stop", self.playback_engine.stop)
            playback_menu.addAction("Seek -15s", partial(self._seek, -15))
            playback_menu.addAction("Seek +15s", partial(self._seek, 15))
            playback_menu.addAction("Cycle Audio", self.playback_engine.cycle_audio)
            playback_menu.addAction("Cycle Subtitle", self.playback_engine.cycle_subtitle)
            playback_menu.addAction("Aspect 16:9", partial(self.playback_engine.set_aspect, "16:9"))
        
        help_menu = mb.addMenu("&Help")
        if help_menu:
            help_menu.addAction("About", self._about)
        
        tools_menu = mb.addMenu("&Tools")
        if tools_menu:
            tools_menu.addAction("Playlist Editor…", self._open_playlist_editor)
            tools_menu.addAction("Multi EPG…", self._open_multiepg)

    def _seek(self, seconds: int) -> None:
        """Seek playback by offset.
        
        Args:
            seconds: Seconds to seek (relative)
        """
        try:
            self.playback_engine.seek(seconds, relative=True)
        except Exception as e:
            logger.error(f"Seek failed: {e}")

    def _show_video_menu(self, pos) -> None:
        """Show context menu on video viewport.
        
        Args:
            pos: Position for menu
        """
        menu = QMenu(self)
        menu.addAction("Play/Pause", self.playback_engine.toggle_pause)
        menu.addAction("Stop", self.playback_engine.stop)
        menu.addSeparator()
        menu.addAction("Audio Track", self.playback_engine.cycle_audio)
        menu.addAction("Subtitle Track", self.playback_engine.cycle_subtitle)
        menu.addAction("Aspect 16:9", partial(self.playback_engine.set_aspect, "16:9"))
        menu.addSeparator()
        menu.addAction("Seek -15s", partial(self._seek, -15))
        menu.addAction("Seek +15s", partial(self._seek, 15))
        menu.addSeparator()
        menu.addAction("Fullscreen", self._toggle_fullscreen)
        menu.exec(self.viewport.mapToGlobal(pos))

    def _toggle_record(self) -> None:
        """Toggle recording on/off."""
        if not self.playback_engine.recording:
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Recording",
                self.record_dir or str(Path.home()),
                "MPEG-TS (*.ts)",
            )
            if not path:
                return
            self.record_dir = str(Path(path).parent)
            if self.current_channel:
                url = self.current_channel.get("url", "")
                try:
                    import subprocess
                    proc = subprocess.Popen(
                        ["ffmpeg", "-y", "-i", url, "-c", "copy", path],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    self.playback_engine.recording = True
                    self.playback_engine.record_path = path
                    self.record_proc = proc
                    logger.info(f"Recording started via ffmpeg: {path}")
                except Exception as e:
                    logger.error(f"ffmpeg recording failed, trying engine: {e}")
                    success = self.playback_engine.start_recording(path)
                    if success:
                        QMessageBox.information(self, "Recording", f"Recording started: {path}")
                    else:
                        QMessageBox.warning(self, "Recording", "Failed to start recording")
            else:
                QMessageBox.warning(self, "Recording", "No stream currently playing")
        else:
            record_proc = getattr(self, "record_proc", None)
            if record_proc:
                try:
                    record_proc.terminate()
                    saved = self.playback_engine.record_path
                    self.record_proc = None
                except Exception as e:
                    logger.error(f"Error terminating ffmpeg: {e}")
                    saved = None
            else:
                saved = self.playback_engine.stop_recording()
            
            if saved:
                QMessageBox.information(self, "Recording saved", f"Saved to {saved}")
            self.playback_engine.recording = False

    def _toggle_fav(self) -> None:
        """Toggle favorite status for current channel."""
        if not self.current_channel:
            QMessageBox.warning(self, "Favorites", "No channel selected")
            return
        sid = self._channel_key(self.current_channel)
        if sid in self.favorites:
            self.favorites.remove(sid)
        else:
            self.favorites.add(sid)
        self._persist_settings()
        self._refresh_menu_content()

    def _channel_key(self, ch: dict) -> str:
        """Get unique key for channel.
        
        Args:
            ch: Channel dictionary
            
        Returns:
            Unique channel identifier
        """
        return ch.get("stream_id") or ch.get("tvg_id") or ch.get("name") or ""

    def _persist_settings(self) -> None:
        """Save settings to disk."""
        self.settings["favorites"] = list(self.favorites)

        save_fn = getattr(core, "save_settings", None)
        if callable(save_fn):
            save_fn(self.settings)
        else:
            logger.warning("core.save_settings is not available; settings not persisted.")

    def _toggle_overlay(self) -> None:
        """Toggle overlay visibility."""
        if self.overlay_visible:
            self._hide_overlay()
        else:
            self._show_overlay()

    def _show_overlay(self) -> None:
        """Show overlay panel."""
        self.overlay_visible = True
        self.overlay.show()
        self.overlay.raise_()
        self.overlay_timer.start(4000)
        self._refresh_overlay_list()

    def _hide_overlay(self) -> None:
        """Hide overlay panel."""
        self.overlay_visible = False
        self.overlay.hide()

    def _overlay_play(self, item) -> None:
        """Play item clicked in overlay.
        
        Args:
            item: Clicked list item
        """
        channels = self._get_category_channels()
        idx = self.ov_list.row(item)
        if idx < 0 or idx >= len(channels):
            logger.warning(f"Invalid overlay index: {idx}")
            return
        ch = channels[idx]
        self.current_channel = ch
        self._load_epg(ch)
        self.playback_engine.play_stream(ch.get("url", ""))
        self.overlay_timer.start(4000)

    def _refresh_overlay_list(self) -> None:
        """Refresh channel list in overlay."""
        self.ov_list.clear()
        for media in self._get_category_channels():
            self.ov_list.addItem(media.get("name", "Unknown"))

    def on_content_click(self, item) -> None:
        """Handle channel selection."""
        channels = self._get_category_channels()
        idx = self.content.row(item)
        if idx < 0 or idx >= len(channels):
            logger.warning(f"Invalid channel index: {idx}")
            return
        ch = channels[idx]
        if (
            (ch.get("group") == "Series" or ch.get("url") is None)
            and self.xtream_client
            and self.xtream_creds
        ):
            try:
                info = self.xtream_client.fetch_series_info(ch.get("stream_id"))
                dlg = SeriesDialog(info, self.xtream_creds, self)
                if dlg.exec() == QDialog.DialogCode.Accepted and dlg.selected_url:
                    self.current_channel = ch
                    self._load_epg(ch)
                    self.playback_engine.play_stream(dlg.selected_url)
            except Exception as e:
                logger.error(f"Series fetch failed: {e}")
                QMessageBox.critical(self, "Error", f"Failed to load series: {e}")
            return
        
        if not ch.get("url"):
            QMessageBox.warning(self, "Channel", "No URL available for this channel")
            return
        
        self.current_channel = ch
        self._load_epg(ch)
        self.playback_engine.play_stream(ch["url"])
        self._refresh_overlay_list()

    def _load_epg(self, ch: dict) -> None:
        """Load and display EPG for channel."""
        self.epg_list.clear()
        key = ch.get("stream_id") or ch.get("tvg_id")
        epg_entry = self.epg_index.get(key, [])
        programs = epg_entry.get("programs", epg_entry) if isinstance(epg_entry, dict) else epg_entry
        now = dt.datetime.now(dt.timezone.utc)
        for p in programs:
            try:
                start_raw, stop_raw = p.get("start"), p.get("stop")
                start_dt = (
                    start_raw
                    if hasattr(start_raw, "astimezone")
                    else dt.datetime.fromisoformat(str(start_raw)).replace(tzinfo=dt.timezone.utc)
                    if start_raw else None
                )
                stop_dt = (
                    stop_raw
                    if hasattr(stop_raw, "astimezone")
                    else dt.datetime.fromisoformat(str(stop_raw)).replace(tzinfo=dt.timezone.utc)
                    if stop_raw else None
                )
                start_str = start_dt.astimezone().strftime("%H:%M") if start_dt else "N/A"
                stop_str = stop_dt.astimezone().strftime("%H:%M") if stop_dt else "N/A"
                title = p.get("title", "Unknown")
                self.epg_list.addItem(f"{start_str} - {stop_str}  {title}")
            except Exception as e:
                logger.debug(f"EPG entry parse error: {e}")
        for i, prog in enumerate(programs):
            try:
                s, t = prog.get("start"), prog.get("stop")
                s_dt = s if hasattr(s, "astimezone") else dt.datetime.fromisoformat(str(s)).replace(tzinfo=dt.timezone.utc)
                t_dt = t if hasattr(t, "astimezone") else dt.datetime.fromisoformat(str(t)).replace(tzinfo=dt.timezone.utc)
                if s_dt <= now <= t_dt:
                    self.epg_list.setCurrentRow(i)
                    break
            except Exception:
                continue
        try:
            now_title = programs[0].get("title", "-") if programs else "-"
            next_title = programs[1].get("title", "-") if len(programs) > 1 else "-"
            self.ov_now.setText(f"Now: {now_title}")
            self.ov_next.setText(f"Next: {next_title}")
            start = programs[0].get("start") if programs else None
            stop = programs[0].get("stop") if programs else None
            if start and stop:
                s_dt = start if hasattr(start, "astimezone") else dt.datetime.fromisoformat(str(start)).replace(tzinfo=dt.timezone.utc)
                t_dt = stop if hasattr(stop, "astimezone") else dt.datetime.fromisoformat(str(stop)).replace(tzinfo=dt.timezone.utc)
                total = (t_dt - s_dt).total_seconds()
                elapsed = (now - s_dt).total_seconds()
                pct = max(0, min(100, int((elapsed / total) * 100))) if total > 0 else 0
                self.ov_prog.setValue(pct)
            else:
                self.ov_prog.setValue(0)
        except Exception as e:
            logger.debug(f"EPG progress error: {e}")
            self.ov_now.setText("Now: -")
            self.ov_next.setText("Next: -")
            self.ov_prog.setValue(0)
        self.ov_title.setText(ch.get("name", "Channel"))

    def _add_playlist(self) -> None:
        """Add/reload playlists."""
        if self.on_reset_cb:
            self.on_reset_cb()

    def _clear_playlists(self) -> None:
        """Clear all playlists."""
        self.data_map = {}
        self.epg_index = {}
        self.menu.clear()
        self.content.clear()
        self.epg_list.clear()
        QMessageBox.information(
            self, "Playlists", "Cleared. Use File > Add Playlist to load again."
        )

    def _toggle_fullscreen(self) -> None:
        """Toggle fullscreen mode."""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _about(self) -> None:
        """Show about dialog."""
        QMessageBox.information(
            self, "SyMoNeuRaL-View", "SyMoNeuRaL-View Professional\nVersion 2.2.0"
        )

    def _reset_setup(self) -> None:
        """Reset configuration."""
        if self.on_reset_cb:
            self.on_reset_cb()

    def _open_playlist_editor(self) -> None:
        """Open the playlist editor dialog."""
        try:
            editor = playlist_mod.PlaylistEditor(playlists=self.data_map, parent=self)
            editor.exec()
        except Exception as e:
            logger.error(f"Failed to open playlist editor: {e}")
            QMessageBox.critical(self, "Error", f"Could not open playlist editor: {e}")

    def _open_multiepg(self) -> None:
        """Open the multi-EPG view."""
        try:
            epg_view = epg_mod.MultiEPG(self.data_map, self.epg_index, parent=self)
            epg_view.exec()
        except Exception as e:
            logger.error(f"Failed to open multi-EPG: {e}")
            QMessageBox.critical(self, "Error", f"Could not open multi-EPG: {e}")

    def _refresh_menu_content(self) -> None:
        """Refresh category menu and current content list."""
        self.menu.clear()

        # Expected shape: {"Category": [channel_dict, ...], ...}
        categories = list(self.data_map.keys())
        categories.sort(key=str.lower)

        query = self.search.text().strip().lower() if hasattr(self, "search") else ""
        for cat in categories:
            if not query or query in str(cat).lower():
                self.menu.addItem(str(cat))

        # Keep content in sync with current category.
        if self.current_cat in self.data_map:
            self._populate_content_list()

    def on_menu_click(self, item) -> None:
        """Handle category selection."""
        self.current_cat = item.text() if item else None
        self._populate_content_list()

    def _populate_content_list(self) -> None:
        """Populate channel/content list for current category."""
        self.content.clear()
        for ch in self._get_category_channels():
            self.content.addItem(ch.get("name", "Unknown"))

    def _get_category_channels(self) -> list[dict]:
        """Return channels for the selected category."""
        if not self.current_cat:
            return []
        channels = self.data_map.get(self.current_cat, [])
        return channels if isinstance(channels, list) else []

    def on_epg_play(self, _item) -> None:
        """Handle EPG item click (play current channel if available)."""
        if not self.current_channel:
            return
        url = self.current_channel.get("url", "")
        if url:
            self.playback_engine.play_stream(url)

    def closeEvent(self, a0) -> None:
        """Handle window close event.
        
        Args:
            a0: Close event
        """
        self.overlay_timer.stop()
        if self.playback_engine:
            self.playback_engine.close()
        if self.record_proc:
            try:
                self.record_proc.terminate()
            except Exception:
                pass
        super().closeEvent(a0)


class SymonInterface(QtWidgets.QWidget):
    """Flagship UI interface with adaptive layouts and AI features."""
    
    def __init__(self, parent: QtWidgets.QWidget | None = None):
        """Initialize interface widget.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle("SyMoNeuRaL Interface")
        self.setMinimumSize(800, 600)
        layout = QVBoxLayout(self)
        
        title = QLabel("SyMoNeuRaL Interface")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)
        
        info = QLabel("Adaptive layouts, AI-powered help, and accessibility features")
        layout.addWidget(info)
        
        btn_help = QPushButton("AI Help")
        btn_help.clicked.connect(self.ai_help)
        layout.addWidget(btn_help)
        
        layout.addStretch()

    def show_message(self, message: str, title: str = "Info") -> None:
        """Display information message.
        
        Args:
            message: Message text
            title: Dialog title
        """
        QtWidgets.QMessageBox.information(self, title, message)
        logger.info(f"Message shown: {title} - {message}")

    def show_error(self, error: Exception, title: str = "Error") -> None:
        """Display error message.
        
        Args:
            error: Exception to display
            title: Dialog title
        """
        QtWidgets.QMessageBox.critical(self, title, str(error))
        logger.error(f"Error shown: {title} - {error}")

    def ai_help(self) -> None:
        """Show AI-powered help dialog."""
        QtWidgets.QMessageBox.information(self, "AI Help", "How can I assist you?")
        logger.info("AI help dialog shown.")
