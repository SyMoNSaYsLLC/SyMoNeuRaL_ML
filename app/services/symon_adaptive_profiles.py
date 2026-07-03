from __future__ import annotations

import os
import re
from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class RuntimeProfile:
    role: str
    name: str
    route: str
    reason: str
    env: dict[str, str]
    options: dict[str, Any]


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return default


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "force", "max"}


def _has(text: str, terms: list[str]) -> bool:
    t = (text or "").lower()
    return any(x in t for x in terms)


def _text_ctx(role: str, chosen: int) -> int:
    """
    Adaptive prompts are allowed to raise work quality, not drop the RTX 5070 Ti
    back to an 8GB conservative profile. When SYMON_FORCE_TEXT_MAX=1, every
    manager/writer/helper/code profile keeps the permanent floor from env.
    """
    if not _env_bool("SYMON_FORCE_TEXT_MAX", True):
        return chosen

    floors = [
        _env_int("SYMON_MIN_TEXT_CTX", chosen),
        _env_int("SYMON_LLAMA_CTX", chosen),
    ]
    if role in {"manager", "writer", "helper"}:
        floors.extend([
            _env_int("SYMON_WRITER_CTX", chosen),
            _env_int("SYMON_CHAT_CTX", chosen),
        ])
    if role == "code":
        floors.append(_env_int("SYMON_CODE_CTX", chosen))

    return max([chosen, *floors])


def _text_batch(role: str, default: int) -> str:
    if role == "code":
        return os.getenv("SYMON_CODE_BATCH", os.getenv("SYMON_LLAMA_BATCH", str(default)))
    return os.getenv("SYMON_WRITER_BATCH", os.getenv("SYMON_CHAT_BATCH", os.getenv("SYMON_LLAMA_BATCH", str(default))))


def _text_ubatch(role: str, default: int) -> str:
    if role == "code":
        return os.getenv("SYMON_CODE_UBATCH", os.getenv("SYMON_LLAMA_UBATCH", str(default)))
    return os.getenv("SYMON_WRITER_UBATCH", os.getenv("SYMON_CHAT_UBATCH", os.getenv("SYMON_LLAMA_UBATCH", str(default))))


def _text_parallel(role: str, default: int) -> str:
    if role == "code":
        return os.getenv("SYMON_CODE_NP", os.getenv("SYMON_CODE_PARALLEL", os.getenv("SYMON_LLAMA_PARALLEL", str(default))))
    return os.getenv("SYMON_WRITER_NP", os.getenv("SYMON_WRITER_PARALLEL", os.getenv("SYMON_CHAT_PARALLEL", os.getenv("SYMON_LLAMA_PARALLEL", str(default)))))


def _explicit_size(prompt: str) -> tuple[int, int] | None:
    m = re.search(r"\b([5-9]\d{2}|1[0-5]\d{2}|16[0-3]\d)\s*(?:x|×|by)\s*([5-9]\d{2}|1[0-5]\d{2}|16[0-3]\d)\b", (prompt or "").lower())
    if not m:
        return None
    max_dim = _env_int("SYMON_IMAGE_MAX_DIM", 1216)
    w = max(256, min(max_dim, int(m.group(1))))
    h = max(256, min(max_dim, int(m.group(2))))
    return max(256, (w // 64) * 64), max(256, (h // 64) * 64)


def normalize_prompt(prompt: str, clean: str | None = None) -> str:
    return f"{prompt or ''}\n{clean or ''}".strip().lower()


def choose_manager_profile(prompt: str, clean: str | None = None) -> RuntimeProfile:
    text = normalize_prompt(prompt, clean)
    if _has(text, ["deep", "analyze", "architecture", "compare", "reason", "debug", "review", "production", "openembedded", "bitbake"]):
        name, ctx, max_tokens, reason = "deep", 16384, 1800, "deep manager/reasoning prompt"
    elif _has(text, ["quick", "short", "simple", "rewrite", "summarize", "one sentence"]):
        name, ctx, max_tokens, reason = "fast", 8192, 900, "quick manager prompt"
    else:
        name, ctx, max_tokens, reason = "balanced", 8192, 1200, "balanced manager default"
    ctx = _text_ctx("manager", ctx)
    return RuntimeProfile("manager", name, "writer", reason, {
        "SYMON_CHAT_CTX": str(ctx),
        "SYMON_WRITER_CTX": str(ctx),
        "SYMON_WRITER_MAX_TOKENS": str(max_tokens),
        "SYMON_CHAT_GPU_LAYERS": "999",
        "SYMON_WRITER_GPU_LAYERS": "999",
        "SYMON_WRITER_BATCH": _text_batch("writer", 4096),
        "SYMON_WRITER_UBATCH": _text_ubatch("writer", 512),
        "SYMON_WRITER_NP": _text_parallel("writer", 2),
    }, {"max_tokens": max_tokens, "temperature": 0.2})


def choose_writer_profile(prompt: str, clean: str | None = None) -> RuntimeProfile:
    text = normalize_prompt(prompt, clean)
    if _has(text, ["book", "long", "full documentation", "complete guide", "detailed report", "architecture", "production"]):
        name, ctx, max_tokens, reason = "longform", 16384, 2200, "long-form writer output"
    elif _has(text, ["quick", "short", "one sentence", "rewrite", "simple"]):
        name, ctx, max_tokens, reason = "fast", 8192, 900, "short writer output"
    else:
        name, ctx, max_tokens, reason = "balanced", 8192, 1400, "balanced writer output"
    ctx = _text_ctx("writer", ctx)
    return RuntimeProfile("writer", name, "writer", reason, {
        "SYMON_CHAT_CTX": str(ctx),
        "SYMON_WRITER_CTX": str(ctx),
        "SYMON_WRITER_MAX_TOKENS": str(max_tokens),
        "SYMON_CHAT_GPU_LAYERS": "999",
        "SYMON_WRITER_GPU_LAYERS": "999",
        "SYMON_WRITER_BATCH": _text_batch("writer", 4096),
        "SYMON_WRITER_UBATCH": _text_ubatch("writer", 512),
        "SYMON_WRITER_NP": _text_parallel("writer", 2),
    }, {"max_tokens": max_tokens, "temperature": 0.25})


def choose_helper_profile(prompt: str, clean: str | None = None) -> RuntimeProfile:
    text = normalize_prompt(prompt, clean)
    if _has(text, ["diagnose", "doctor", "logs", "performance", "benchmark", "nvidia-smi", "vram", "cpu"]):
        name, ctx, reason = "diagnostic", 16384, "diagnostic/helper workload"
    else:
        name, ctx, reason = "normal", 8192, "normal helper workload"
    ctx = _text_ctx("helper", ctx)
    return RuntimeProfile("helper", name, "writer", reason, {
        "SYMON_HELPER_CTX": str(ctx),
        "SYMON_WRITER_CTX": str(ctx),
        "SYMON_CHAT_CTX": str(ctx),
        "SYMON_WRITER_BATCH": _text_batch("writer", 4096),
        "SYMON_WRITER_UBATCH": _text_ubatch("writer", 512),
        "SYMON_WRITER_NP": _text_parallel("writer", 2),
    }, {"max_tokens": 1400})


def choose_code_profile(prompt: str, clean: str | None = None) -> RuntimeProfile:
    text = normalize_prompt(prompt, clean)
    if _has(text, ["entire repo", "whole repo", "production", "shipping", "openembedded", "bitbake", "yocto", "cmake", "cuda", "full update", "merge", "major backend"]):
        name, ctx, max_tokens, reason = "repo-heavy", 32768, 4096, "repo/build/production code request"
    elif _has(text, ["patch", "hotfix", "script", "test.py", "bench.py", "small", "simple", "hello-world"]):
        name, ctx, max_tokens, reason = "fast-code", 16384, 2600, "small code/script request"
    else:
        name, ctx, max_tokens, reason = "balanced-code", 24576, 3200, "balanced code request"
    ctx = _text_ctx("code", ctx)
    return RuntimeProfile("code", name, "code", reason, {
        "SYMON_CODE_CTX": str(ctx),
        "SYMON_CODE_GPU_LAYERS": "999",
        "SYMON_CODE_BATCH": _text_batch("code", 4096),
        "SYMON_CODE_UBATCH": _text_ubatch("code", 512),
        "SYMON_CODE_NP": _text_parallel("code", 1),
        "SYMON_CODER_MAX_TOKENS": str(max_tokens),
    }, {"max_tokens": max_tokens, "temperature": 0.15})


def choose_image_profile(prompt: str, requested: dict[str, Any] | None = None) -> RuntimeProfile:
    requested = dict(requested or {})
    text = (prompt or "").strip()
    low = text.lower()
    forced = os.getenv("SYMON_IMAGE_PROFILE", "").strip().lower()
    explicit = _explicit_size(text)

    fast_words = ["quick", "fast", "draft", "preview", "rough", "test image", "simple", "thumbnail", "icon", "sketch"]
    quality_words = ["professional", "cinematic", "photorealistic", "photo realistic", "ultra detailed", "high detail", "high quality", "wallpaper", "poster", "cover art", "product shot", "realistic", "8k", "4k", "masterpiece", "sharp", "detailed"]
    max_words = ["final", "print", "production", "portfolio", "best quality", "top notch", "very detailed", "extremely detailed", "large image", "high resolution"]
    stress_words = ["stress", "benchmark", "max vram", "14gb", "14 gb", "use all vram", "vram target", "maximum vram"]

    profiles = {
        "fast": ("fast", _env_int("SYMON_IMAGE_FAST_WIDTH", 768), _env_int("SYMON_IMAGE_FAST_HEIGHT", 768), _env_int("SYMON_IMAGE_FAST_STEPS", 24), _env_float("SYMON_IMAGE_FAST_CFG", 7.0), "fast/preview image prompt"),
        "balanced": ("balanced", _env_int("SYMON_IMAGE_BALANCED_WIDTH", 1152), _env_int("SYMON_IMAGE_BALANCED_HEIGHT", 1152), _env_int("SYMON_IMAGE_BALANCED_STEPS", 40), _env_float("SYMON_IMAGE_BALANCED_CFG", 7.5), "balanced image default"),
        "quality": ("quality", _env_int("SYMON_IMAGE_QUALITY_WIDTH", 1152), _env_int("SYMON_IMAGE_QUALITY_HEIGHT", 1152), _env_int("SYMON_IMAGE_QUALITY_STEPS", 40), _env_float("SYMON_IMAGE_QUALITY_CFG", 7.5), "professional/high-quality image prompt"),
        "max": ("max", _env_int("SYMON_IMAGE_MAX_WIDTH", 1216), _env_int("SYMON_IMAGE_MAX_HEIGHT", 1216), _env_int("SYMON_IMAGE_MAX_STEPS", 40), _env_float("SYMON_IMAGE_MAX_CFG", 7.5), "maximum image detail prompt"),
        "stress": ("stress", _env_int("SYMON_IMAGE_STRESS_WIDTH", 1216), _env_int("SYMON_IMAGE_STRESS_HEIGHT", 1216), _env_int("SYMON_IMAGE_STRESS_STEPS", 40), _env_float("SYMON_IMAGE_STRESS_CFG", 7.5), "VRAM stress/benchmark image prompt"),
    }

    if forced in profiles:
        name, width, height, steps, cfg, reason = profiles[forced]
    elif _has(low, stress_words):
        name, width, height, steps, cfg, reason = profiles["stress"]
    elif _has(low, max_words):
        name, width, height, steps, cfg, reason = profiles["max"]
    elif _has(low, quality_words):
        name, width, height, steps, cfg, reason = profiles["quality"]
    elif _has(low, fast_words):
        name, width, height, steps, cfg, reason = profiles["fast"]
    else:
        name, width, height, steps, cfg, reason = profiles["balanced"]

    if explicit:
        width, height = explicit
    if requested.get("width"):
        width = int(requested["width"])
    if requested.get("height"):
        height = int(requested["height"])
    if requested.get("steps"):
        steps = int(requested["steps"])
    if requested.get("cfg_scale"):
        cfg = float(requested["cfg_scale"])

    max_dim = _env_int("SYMON_IMAGE_MAX_DIM", 1216)
    width = max(256, min(max_dim, (int(width) // 64) * 64))
    height = max(256, min(max_dim, (int(height) // 64) * 64))
    max_pixels = _env_int("SYMON_IMAGE_MAX_PIXELS", max_dim * max_dim)
    if width * height > max_pixels:
        scale = (max_pixels / float(width * height)) ** 0.5
        width = max(256, int(width * scale) // 64 * 64)
        height = max(256, int(height * scale) // 64 * 64)

    return RuntimeProfile("image", name, "image", reason, {
        "SYMON_IMAGE_WIDTH": str(width),
        "SYMON_IMAGE_HEIGHT": str(height),
        "SYMON_IMAGE_STEPS": str(steps),
        "SYMON_IMAGE_CFG_SCALE": str(cfg),
    }, {"width": width, "height": height, "steps": steps, "cfg_scale": cfg})


def choose_profile(route: str, prompt: str, clean: str | None = None, options: dict[str, Any] | None = None, phase: str | None = None) -> RuntimeProfile:
    route = (route or "").strip().lower()
    phase = (phase or "").strip().lower()
    if route == "code":
        return choose_code_profile(prompt, clean)
    if route == "image":
        return choose_image_profile(clean or prompt, options)
    if phase == "helper":
        return choose_helper_profile(prompt, clean)
    if phase == "manager":
        return choose_manager_profile(prompt, clean)
    return choose_writer_profile(prompt, clean)


def apply_runtime_env(profile: RuntimeProfile) -> RuntimeProfile:
    for k, v in profile.env.items():
        os.environ[str(k)] = str(v)
    return profile


def profile_dict(profile: RuntimeProfile) -> dict[str, Any]:
    return asdict(profile)


def profile_log(profile: RuntimeProfile) -> str:
    if profile.role == "image":
        return f"[profile] {profile.role}/{profile.name}: {profile.options.get('width')}x{profile.options.get('height')} steps={profile.options.get('steps')} reason={profile.reason}"
    if profile.role == "code":
        return f"[profile] {profile.role}/{profile.name}: ctx={profile.env.get('SYMON_CODE_CTX')} batch={profile.env.get('SYMON_CODE_BATCH')} np={profile.env.get('SYMON_CODE_NP')} max_tokens={profile.options.get('max_tokens')} reason={profile.reason}"
    return f"[profile] {profile.role}/{profile.name}: ctx={profile.env.get('SYMON_WRITER_CTX') or profile.env.get('SYMON_CHAT_CTX')} batch={profile.env.get('SYMON_WRITER_BATCH')} np={profile.env.get('SYMON_WRITER_NP')} max_tokens={profile.options.get('max_tokens')} reason={profile.reason}"


def apply_image_profile(prompt: str, options: dict[str, Any] | None = None) -> dict[str, Any]:
    profile = choose_image_profile(prompt, options)
    apply_runtime_env(profile)
    out = dict(options or {})
    out.update(profile.options)
    out["_profile"] = profile.name
    out["_profile_reason"] = profile.reason
    return out
