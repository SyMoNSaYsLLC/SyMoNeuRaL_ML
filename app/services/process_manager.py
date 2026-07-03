from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("SyMoNeuRaL.ProcessManager")


class EngineProcessManager:
    """
    Process manager for exclusive-VRAM orchestration.

    Default production mode:
      - keep only the writer/manager engine resident
      - stop writer before launching code or image
      - stop code/image and restart writer for assessment/user response
    """

    def __init__(self, root: Path, engines: dict[str, Any], raw_config: dict[str, Any] | None = None):
        self.root = root
        self.engines = engines
        self.raw_config = raw_config or {}
        orch = self.raw_config.get("orchestration", {})
        self.exclusive_vram = bool(orch.get("exclusive_vram", True))
        self.resident_engine = str(orch.get("resident_engine", "writer"))
        self.processes: dict[str, subprocess.Popen] = {}
        self.lock = threading.RLock()

    def shared_library_dirs(self) -> list[str]:
        dirs: set[str] = set()
        for base in [self.root / "engines" / "llama.cpp" / "build", self.root / "engines" / "stable-diffusion.cpp" / "build"]:
            if base.exists():
                for path in base.rglob("*.so"):
                    if path.is_file():
                        dirs.add(str(path.parent.resolve()))
        return sorted(dirs)

    def env(self) -> dict[str, str]:
        env = os.environ.copy()
        lib_dirs = self.shared_library_dirs()
        if lib_dirs:
            env["LD_LIBRARY_PATH"] = ":".join(lib_dirs + ([env.get("LD_LIBRARY_PATH", "")] if env.get("LD_LIBRARY_PATH") else []))
        return env

    def _replace_flag(self, cmd: list[str], old: set[str], new: str) -> list[str]:
        return [new if item in old else item for item in cmd]

    def _has_any(self, cmd: list[str], flags: set[str]) -> bool:
        return any(x in flags for x in cmd)

    def _set_or_append(self, cmd: list[str], flag: str, value: str) -> list[str]:
        aliases = {flag, "--ngl", "-ngl"} if flag == "--gpu-layers" else {flag}
        out: list[str] = []
        replaced = False
        i = 0
        while i < len(cmd):
            if cmd[i] in aliases:
                out.extend([flag, str(value)])
                i += 2
                replaced = True
            else:
                out.append(cmd[i])
                i += 1
        if not replaced:
            out.extend([flag, str(value)])
        return out

    def normalize_cmd(self, name: str, cmd: list[str]) -> list[str]:
        cmd = list(cmd)
        binary = Path(cmd[0]).name
        if binary == "llama-server":
            cmd = self._replace_flag(cmd, {"--ngl", "-ngl"}, "--gpu-layers")
            env_prefix = name.upper()

            gpu_layers = os.getenv(f"SYMON_{env_prefix}_GPU_LAYERS")
            # Browser convention aliases from local-ai.
            if name == "writer" and not gpu_layers:
                gpu_layers = os.getenv("SYMON_CHAT_GPU_LAYERS")
            if name == "code" and not gpu_layers:
                gpu_layers = os.getenv("SYMON_CODE_GPU_LAYERS")

            if gpu_layers:
                cmd = self._set_or_append(cmd, "--gpu-layers", gpu_layers)

            if not self._has_any(cmd, {"-c", "--ctx-size"}):
                ctx = (
                    os.getenv(f"SYMON_{env_prefix}_CTX")
                    or (os.getenv("SYMON_CHAT_CTX") if name == "writer" else None)
                    or os.getenv("SYMON_DEFAULT_CTX", "4096")
                )
                cmd.extend(["-c", ctx])
            if not self._has_any(cmd, {"-np", "--parallel"}):
                cmd.extend(["-np", os.getenv(f"SYMON_{env_prefix}_NP", "1")])
            if not self._has_any(cmd, {"-b", "--batch-size"}):
                batch = (
                    os.getenv(f"SYMON_{env_prefix}_BATCH")
                    or (os.getenv("SYMON_CHAT_BATCH") if name == "writer" else None)
                    or (os.getenv("SYMON_CODE_BATCH") if name == "code" else None)
                    or os.getenv("SYMON_DEFAULT_BATCH", "512")
                )
                cmd.extend(["-b", batch])
            if not self._has_any(cmd, {"-ub", "--ubatch-size"}):
                ubatch = (
                    os.getenv(f"SYMON_{env_prefix}_UBATCH")
                    or (os.getenv("SYMON_CHAT_UBATCH") if name == "writer" else None)
                    or (os.getenv("SYMON_CODE_UBATCH") if name == "code" else None)
                    or os.getenv("SYMON_DEFAULT_UBATCH", "128")
                )
                cmd.extend(["-ub", ubatch])
        return cmd

    async def start_all(self) -> None:
        if self.exclusive_vram:
            logger.info("Exclusive VRAM mode enabled; starting resident engine only: %s", self.resident_engine)
            self.start_engine_sync(self.resident_engine)
            return

        for name in self.engines:
            self.start_engine_sync(name)
            await asyncio.sleep(0.7)

    async def stop_all(self) -> None:
        self.stop_all_sync()

    def start_engine_sync(self, name: str) -> None:
        with self.lock:
            cfg = self.engines.get(name)
            if not cfg:
                raise KeyError(f"Engine not configured: {name}")
            if not cfg.get("enabled", True):
                logger.info("Skipping disabled engine %s", name)
                return
            proc = self.processes.get(name)
            if proc and proc.poll() is None:
                logger.info("Engine %s already running pid=%s", name, proc.pid)
                return
            cmd = self.normalize_cmd(name, cfg["cmd"])
            logger.info("Starting %s: %s", name, " ".join(cmd))
            self.processes[name] = subprocess.Popen(cmd, cwd=str(self.root), env=self.env(), text=True)
        time.sleep(float(os.getenv("SYMON_ENGINE_START_GRACE", "0.9")))

    def stop_engine_sync(self, name: str) -> None:
        with self.lock:
            proc = self.processes.get(name)
            if not proc or proc.poll() is not None:
                return
            logger.info("Stopping %s pid=%s", name, proc.pid)
            proc.terminate()
        try:
            proc.wait(timeout=float(os.getenv("SYMON_ENGINE_STOP_TIMEOUT", "8")))
        except subprocess.TimeoutExpired:
            logger.warning("Force killing %s pid=%s", name, proc.pid)
            proc.kill()
            proc.wait(timeout=3)

    def stop_all_sync(self) -> None:
        for name in list(self.processes):
            self.stop_engine_sync(name)

    def stop_all_except_sync(self, keep: str | None) -> None:
        for name in list(self.processes):
            if keep and name == keep:
                continue
            self.stop_engine_sync(name)

    def switch_exclusive_sync(self, name: str) -> None:
        """Give one engine the GPU by stopping every other managed engine, then starting target."""
        with self.lock:
            names = list(self.engines.keys())
        for other in names:
            if other != name:
                self.stop_engine_sync(other)
        self.start_engine_sync(name)

    def restart_resident_sync(self) -> None:
        if self.resident_engine:
            self.switch_exclusive_sync(self.resident_engine)

    def status(self) -> dict[str, Any]:
        with self.lock:
            result = {}
            for name in self.engines:
                proc = self.processes.get(name)
                result[name] = {
                    "pid": getattr(proc, "pid", None),
                    "running": bool(proc and proc.poll() is None),
                    "returncode": None if (proc and proc.poll() is None) else (proc.poll() if proc else None),
                    "resident": name == self.resident_engine,
                }
            result["_orchestration"] = {
                "exclusive_vram": self.exclusive_vram,
                "resident_engine": self.resident_engine,
            }
            return result
