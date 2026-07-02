from __future__ import annotations

DEFAULT_NEGATIVE = "worst quality, low quality, blurry, bad anatomy, bad hands, extra fingers, watermark, text, logo"
STYLE = {
    "cinematic": "cinematic film still, dramatic lighting, detailed composition, sharp focus",
    "photo": "professional photo, natural lighting, realistic texture, sharp focus",
    "fantasy": "epic fantasy concept art, high detail, atmospheric",
    "anime": "anime key visual, clean linework, vibrant lighting",
    "none": "",
}


def image_payload_attempts(data: dict) -> list[tuple[str, dict]]:
    prompt = (data.get("prompt") or "").strip()
    style = STYLE.get(data.get("style", "cinematic"), STYLE["cinematic"])
    if data.get("enhance", True) and style:
        prompt = f"{prompt}, {style}, best quality"
    width = max(256, min(1024, int(data.get("width", 512))))
    height = max(256, min(1024, int(data.get("height", 512))))
    width = (width // 64) * 64
    height = (height // 64) * 64
    steps = max(8, min(80, int(data.get("steps", 34))))
    seed = int(data.get("seed", -1) or -1)
    cfg = float(data.get("cfg_scale", 7.5))
    sampler = data.get("sampler_name") or "Euler a"
    negative = data.get("negative_prompt") or DEFAULT_NEGATIVE
    minimal = {"prompt": prompt, "width": width, "height": height, "steps": steps, "seed": seed}
    safe = {**minimal, "negative_prompt": negative, "cfg_scale": cfg}
    full = {**safe, "sampler_name": sampler, "batch_size": 1, "n_iter": 1, "restore_faces": False, "tiling": False}
    if data.get("compat"):
        return [("minimal", minimal)]
    return [("a1111", full), ("sd.cpp-safe", safe), ("minimal", minimal)]
