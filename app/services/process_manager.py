from __future__ import annotations

import asyncio
import logging
import os
import shlex
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("SyMoNeuRaL.ProcessManager")


class EngineProcessManager:
    """
    Process manager for exclusive-VRAM orchestration.

    Important RTX 5070 Ti rule:
      normal writer/code starts must not silently fall back to low-VRAM
      llama.cpp defaults. All llama-compatible engines are normalized from the
      SYMON_* profile every launch, replacing stale -c/-b/-ub/-np args.
    """

    def __init__(self, root: Path, engines: dict[str, Any], raw_config: dict[str, Any] | None = None):
        self.root = root
        self.engines = engines
        self.raw_config = raw_config or {}
        orch = self.raw_config.get("orchestration", {})
        self.exclusive_vram = bool(orch.get("exclusive_vram", True))
        self.resident_engine = str(os.getenv("SYMON_RESIDENT_ENGINE", orch.get("resident_engine", "writer")))
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

    def _flag_aliases(self, flag: str) -> set[str]:
        return {
            "--gpu-layers": {"--gpu-layers", "--ngl", "-ngl"},
            "--ctx-size": {"--ctx-size", "-c"},
            "--parallel": {"--parallel", "-np"},
            "--batch-size": {"--batch-size", "-b"},
            "--ubatch-size": {"--ubatch-size", "-ub"},
        }.get(flag, {flag})

    def _set_or_append(self, cmd: list[str], flag: str, value: str) -> list[str]:
        aliases = self._flag_aliases(flag)
        out: list[str] = []
        replaced = False
        i = 0
        while i < len(cmd):
            item = cmd[i]
            matched_eq = None
            for alias in aliases:
                if item.startswith(alias + "="):
                    matched_eq = alias
                    break
            if item in aliases:
                out.extend([flag, str(value)])
                i += 2
                replaced = True
                continue
            if matched_eq:
                out.extend([flag, str(value)])
                i += 1
                replaced = True
                continue
            out.append(item)
            i += 1
        if not replaced:
            out.extend([flag, str(value)])
        return out

    def _is_llama_cmd(self, name: str, cmd: list[str]) -> bool:
        if not cmd:
            return False
        binary = Path(cmd[0]).name.lower()
        return (
            name in {"writer", "code"}
            or "llama-server" in binary
            or "symon-llm-server" in binary
            or "symon-llama-server" in binary
        )

    def _first_env(self, *names: str, default: str) -> str:
        for name in names:
            value = os.getenv(name)
            if value not in (None, ""):
                return str(value)
        return default

    def normalize_cmd(self, name: str, cmd: list[str]) -> list[str]:
        cmd = list(cmd)
        if self._is_llama_cmd(name, cmd):
            cmd = self._replace_flag(cmd, {"--ngl", "-ngl"}, "--gpu-layers")
            env_prefix = name.upper()

            gpu_layers = self._first_env(
                f"SYMON_{env_prefix}_GPU_LAYERS",
                "SYMON_LLAMA_GPU_LAYERS",
                "SYMON_CHAT_GPU_LAYERS" if name == "writer" else "SYMON_CODE_GPU_LAYERS",
                default="999",
            )
            ctx = self._first_env(
                f"SYMON_{env_prefix}_CTX",
                "SYMON_LLAMA_CTX",
                "SYMON_CHAT_CTX" if name == "writer" else "SYMON_CODE_CTX",
                "SYMON_DEFAULT_CTX",
                default="4096",
            )
            parallel = self._first_env(
                f"SYMON_{env_prefix}_NP",
                f"SYMON_{env_prefix}_PARALLEL",
                "SYMON_LLAMA_NP",
                "SYMON_LLAMA_PARALLEL",
                "SYMON_CHAT_NP" if name == "writer" else "SYMON_CODE_NP",
                "SYMON_CHAT_PARALLEL" if name == "writer" else "SYMON_CODE_PARALLEL",
                default="1",
            )
            batch = self._first_env(
                f"SYMON_{env_prefix}_BATCH",
                "SYMON_LLAMA_BATCH",
                "SYMON_CHAT_BATCH" if name == "writer" else "SYMON_CODE_BATCH",
                "SYMON_DEFAULT_BATCH",
                default="512",
            )
            ubatch = self._first_env(
                f"SYMON_{env_prefix}_UBATCH",
                "SYMON_LLAMA_UBATCH",
                "SYMON_CHAT_UBATCH" if name == "writer" else "SYMON_CODE_UBATCH",
                "SYMON_DEFAULT_UBATCH",
                default="128",
            )

            # Always replace. Do not leave old conservative args in config.yaml.
            cmd = self._set_or_append(cmd, "--gpu-layers", gpu_layers)
            cmd = self._set_or_append(cmd, "--ctx-size", ctx)
            cmd = self._set_or_append(cmd, "--parallel", parallel)
            cmd = self._set_or_append(cmd, "--batch-size", batch)
            cmd = self._set_or_append(cmd, "--ubatch-size", ubatch)

            extra = self._first_env(
                f"SYMON_{env_prefix}_EXTRA_ARGS",
                "SYMON_LLAMA_EXTRA_ARGS",
                default="",
            )
            if extra:
                for token in shlex.split(extra):
                    if token not in cmd:
                        cmd.append(token)

            logger.info(
                "RTX5070Ti profile for %s: gpu_layers=%s ctx=%s parallel=%s batch=%s ubatch=%s extra=%s",
                name, gpu_layers, ctx, parallel, batch, ubatch, extra or "-",
            )
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
