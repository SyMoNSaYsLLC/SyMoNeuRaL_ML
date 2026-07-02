from __future__ import annotations


def is_image_intent(prompt: str) -> bool:
    text = (prompt or "").lower()
    return any(x in text for x in ["image", "picture", "photo", "draw", "stable diffusion", "generate art", "render", "logo"])


def is_background_code_intent(prompt: str) -> bool:
    """Detect when the hidden Qwen coder should build/test after the writer decides the plan."""
    text = (prompt or "").lower()
    code_terms = [
        "code", "python", "bash", "cpp", "c++", "fastapi", "api", "script", "repo", "zip", "tar.gz",
        "build", "test", "patch", "frontend", "backend", "html", "css", "javascript", "js", "bitbake",
        "recipe", "docker", "systemd", "service", "helper", "tool", "fix this", "make this", "create files",
    ]
    return any(term in text for term in code_terms)


def choose_expert(prompt: str, explicit: str | None = None) -> str:
    # Public/frontend routing only exposes writer + image. The code model is a hidden background worker.
    if explicit == "image":
        return "image"
    if explicit in {"writer", "code"}:
        return "writer"
    if is_image_intent(prompt):
        return "image"
    return "writer"
