from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class Settings(BaseModel):
    root: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[2])
    config_path: Path = Field(default_factory=lambda: Path(os.getenv("SYMON_CONFIG", "config.yaml")))
    raw: dict[str, Any] = Field(default_factory=dict)

    @property
    def host(self) -> str:
        return os.getenv("SYMON_HOST", self.raw.get("app", {}).get("host", "0.0.0.0"))

    @property
    def port(self) -> int:
        return int(os.getenv("SYMON_PORT", self.raw.get("app", {}).get("port", 8000)))

    @property
    def require_api_key(self) -> bool:
        env = os.getenv("SYMON_REQUIRE_API_KEY")
        if env is not None:
            return env.lower() in {"1", "true", "yes", "on"}
        return bool(self.raw.get("security", {}).get("require_api_key", False))

    @property
    def api_keys(self) -> set[str]:
        key_env = self.raw.get("security", {}).get("api_key_env", "SYMON_API_KEYS")
        keys = os.getenv(key_env, os.getenv("SYMON_API_KEYS", ""))
        return {k.strip() for k in keys.split(",") if k.strip()}

    @property
    def engines(self) -> dict[str, Any]:
        return self.raw.get("engines", {})


def load_yaml(path: Path) -> dict[str, Any]:
    resolved = path if path.is_absolute() else Path.cwd() / path
    if not resolved.exists():
        fallback = Path(__file__).resolve().parents[2] / "config.yaml"
        resolved = fallback
    with resolved.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    path = Path(os.getenv("SYMON_CONFIG", "config.yaml"))
    return Settings(config_path=path, raw=load_yaml(path))
