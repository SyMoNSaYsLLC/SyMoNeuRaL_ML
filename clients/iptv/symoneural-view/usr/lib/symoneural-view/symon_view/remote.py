"""Remote control via network protocols (HTTP, D-Bus)."""

from __future__ import annotations

import json
import logging
import threading
from typing import Any, Callable

logger = logging.getLogger(__name__)

Handler = Callable[..., dict[str, Any]]


class HTTPRemoteInterface:
    """HTTP remote control server."""

    def __init__(self, port: int = 8080, bind_addr: str = "127.0.0.1"):
        self.port = int(port)
        self.bind_addr = bind_addr
        self.handlers: dict[str, Handler] = {}
        self.server: Any = None
        self.thread: threading.Thread | None = None

    def register_handler(self, command: str, handler: Handler) -> None:
        self.handlers[command] = handler

    def start(self) -> None:
        if self.server is not None:
            return

        try:
            from http.server import BaseHTTPRequestHandler, HTTPServer

            interface_ref = self

            class RemoteHandler(BaseHTTPRequestHandler):
                def _send_json(self, status: int, payload: dict[str, Any]) -> None:
                    raw = json.dumps(payload).encode("utf-8")
                    self.send_response(status)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(raw)))
                    self.end_headers()
                    self.wfile.write(raw)

                def do_GET(self) -> None:  # noqa: N802
                    self._send_json(200, {"success": True, "service": "symoneural-remote", "status": "ok"})

                def do_POST(self) -> None:  # noqa: N802
                    length = int(self.headers.get("Content-Length", 0))
                    body = self.rfile.read(length)

                    try:
                        data = json.loads(body.decode("utf-8")) if body else {}
                        if not isinstance(data, dict):
                            self._send_json(400, {"success": False, "error": "request must be object"})
                            return

                        command = data.get("command")
                        args = data.get("args", {})

                        if not isinstance(command, str) or not command:
                            self._send_json(400, {"success": False, "error": "command must be string"})
                            return

                        if not isinstance(args, dict):
                            self._send_json(400, {"success": False, "error": "args must be object"})
                            return

                        handler = interface_ref.handlers.get(command)
                        if handler is None:
                            self._send_json(404, {"success": False, "error": "unknown command"})
                            return

                        result = handler(**args)
                        self._send_json(200, {"success": True, "result": result})

                    except Exception as e:
                        logger.error(f"Remote command error: {e}")
                        self._send_json(500, {"success": False, "error": str(e)})

                def log_message(self, format: str, *args: Any) -> None:
                    _ = format, args
                    return

            self.server = HTTPServer((self.bind_addr, self.port), RemoteHandler)
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            logger.info(f"HTTP Remote started at {self.bind_addr}:{self.port}")

        except Exception as e:
            self.server = None
            self.thread = None
            logger.error(f"Failed to start HTTP server: {e}")

    def stop(self) -> None:
        if self.server is None:
            return
        try:
            self.server.shutdown()
            self.server.server_close()
        except Exception as e:
            logger.error(f"HTTP stop failed: {e}")
        finally:
            self.server = None
            self.thread = None


class DBusRemoteInterface:
    """D-Bus remote control interface."""

    def __init__(self):
        self.bus: Any = None
        self.bus_name: Any = None
        self.service: Any = None
        self.handlers: dict[str, Handler] = {}

    def register_handler(self, command: str, handler: Handler) -> None:
        self.handlers[command] = handler

    def start(self) -> bool:
        try:
            import dbus  # type: ignore
            import dbus.service  # type: ignore

            self.bus = dbus.SessionBus()
            interface_ref = self

            class SyMoNeuRaLService(dbus.service.Object):
                @dbus.service.method("com.symoneural.RemoteControl", in_signature="ss", out_signature="s")
                def ExecuteCommand(self, command: str, params: str) -> str:  # noqa: N802
                    try:
                        parsed = json.loads(params) if params else {}
                    except Exception:
                        parsed = {}

                    args = parsed if isinstance(parsed, dict) else {}
                    handler = interface_ref.handlers.get(command)
                    if handler is None:
                        return json.dumps({"success": False, "error": "unknown command"})

                    try:
                        result = handler(**args)
                        return json.dumps({"success": True, "result": result})
                    except Exception as e:
                        return json.dumps({"success": False, "error": str(e)})

            self.bus_name = dbus.service.BusName("com.symoneural.RemoteControl", bus=self.bus)
            self.service = SyMoNeuRaLService(self.bus, "/com/symoneural/RemoteControl")
            logger.info("D-Bus service registered")
            return True

        except Exception as e:
            logger.debug(f"D-Bus not available: {e}")
            self.bus = None
            self.bus_name = None
            self.service = None
            return False

    def stop(self) -> None:
        self.service = None
        self.bus_name = None
        self.bus = None


class RemoteControlManager:
    """Central remote control manager."""

    def __init__(self, playback_engine: Any = None):
        self.playback = playback_engine
        self.http_interface = HTTPRemoteInterface()
        self.dbus_interface = DBusRemoteInterface()
        self._register_handlers()

    def _register_handlers(self) -> None:
        handlers: dict[str, Handler] = {
            "play": self._cmd_play,
            "pause": self._cmd_pause,
            "stop": self._cmd_stop,
            "volume": self._cmd_volume,
            "next": self._cmd_next,
            "previous": self._cmd_previous,
            "status": self._cmd_status,
        }

        for cmd, handler in handlers.items():
            self.http_interface.register_handler(cmd, handler)
            self.dbus_interface.register_handler(cmd, handler)

    def _cmd_play(self, url: str | None = None) -> dict[str, Any]:
        if self.playback and url:
            return {"success": bool(self.playback.play(url))}
        return {"success": False, "error": "missing url or playback"}

    def _cmd_pause(self) -> dict[str, Any]:
        if self.playback:
            self.playback.pause()
            return {"success": True}
        return {"success": False}

    def _cmd_stop(self) -> dict[str, Any]:
        if self.playback:
            self.playback.stop()
            return {"success": True}
        return {"success": False}

    def _cmd_volume(self, level: int = 75) -> dict[str, Any]:
        if self.playback:
            return {"success": bool(self.playback.set_volume(level))}
        return {"success": False}

    def _cmd_next(self) -> dict[str, Any]:
        return {"success": True}

    def _cmd_previous(self) -> dict[str, Any]:
        return {"success": True}

    def _cmd_status(self) -> dict[str, Any]:
        if self.playback and hasattr(self.playback, "get_diagnostics"):
            return dict(self.playback.get_diagnostics())
        return {"success": True, "status": "idle"}

    def start(self) -> None:
        self.http_interface.start()
        self.dbus_interface.start()

    def stop(self) -> None:
        self.http_interface.stop()
        self.dbus_interface.stop()