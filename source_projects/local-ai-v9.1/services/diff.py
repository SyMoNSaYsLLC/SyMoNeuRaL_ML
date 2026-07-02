DEFAULT_NEGATIVE = (
    "worst quality, low quality, normal quality, lowres, blurry, pixelated, jpeg artifacts, "
    "bad anatomy, bad hands, extra fingers, missing fingers, extra limbs, malformed, deformed, "
    "duplicate, cropped, out of frame, watermark, text, logo, signature"
)

STYLE_PROMPTS = {
    "cinematic": "cinematic film still, dramatic lighting, detailed composition, atmospheric, sharp focus",
    "photo": "professional photo, natural lighting, high detail, realistic texture, sharp focus",
    "fantasy": "epic fantasy concept art, detailed environment, dramatic atmosphere, high detail",
    "anime": "anime key visual, clean linework, detailed background, vibrant lighting",
    "product": "professional product render, studio lighting, clean background, sharp detail",
    "none": "",
}

SAMPLER_MAP = {
    "Euler A": "Euler a",
    "Euler a": "Euler a",
    "Euler": "Euler",
    "Heun": "Heun",
    "DPM++ 2M": "DPM++ 2M",
    "DPM++ 2M v2": "DPM++ 2M v2",
    "DPM++ 2S a": "DPM++ 2S a",
    "LCM": "LCM",
}


class DiffService:
    name = "stable-diffusion"
    kind = "image"

    def _clean_int(self, value, default):
        try:
            return int(value)
        except Exception:
            return default

    def _clean_float(self, value, default):
        try:
            return float(value)
        except Exception:
            return default

    def _build_prompt(self, data):
        prompt = (data.get("prompt") or "").strip()
        style = (data.get("style") or "cinematic").strip()
        enhance = data.get("enhance", True)
        if isinstance(enhance, str):
            enhance = enhance.lower() not in ("0", "false", "no", "off")
        style_text = STYLE_PROMPTS.get(style, STYLE_PROMPTS["cinematic"])
        if enhance and style_text:
            prompt = f"{prompt}, {style_text}, best quality"
        return prompt

    def _base(self, data):
        seed = data.get("seed", -1)
        if seed in ("", None):
            seed = -1
        seed = self._clean_int(seed, -1)

        width = max(256, min(1024, self._clean_int(data.get("width", 512), 512)))
        height = max(256, min(1024, self._clean_int(data.get("height", 512), 512)))
        width = (width // 64) * 64
        height = (height // 64) * 64

        sampler = (data.get("sampler_name") or "Euler a").strip()
        sampler = SAMPLER_MAP.get(sampler, sampler)

        return {
            "prompt": self._build_prompt(data),
            "negative_prompt": (data.get("negative_prompt") or DEFAULT_NEGATIVE).strip(),
            "width": width,
            "height": height,
            "steps": max(8, min(80, self._clean_int(data.get("steps", 34), 34))),
            "cfg_scale": max(1.0, min(20.0, self._clean_float(data.get("cfg_scale", 7.5), 7.5))),
            "sampler_name": sampler,
            "seed": seed,
        }

    def payload_attempts(self, data):
        base = self._base(data)
        compat = data.get("compat", False)
        if isinstance(compat, str):
            compat = compat.lower() in ("1", "true", "yes", "on")

        minimal = {
            "prompt": base["prompt"],
            "width": base["width"],
            "height": base["height"],
            "steps": base["steps"],
            "seed": base["seed"],
        }
        sdcpp_safe = {
            **minimal,
            "negative_prompt": base["negative_prompt"],
            "cfg_scale": base["cfg_scale"],
        }
        a1111 = {
            **sdcpp_safe,
            "sampler_name": base["sampler_name"],
            "batch_size": 1,
            "n_iter": 1,
            "restore_faces": False,
            "tiling": False,
        }
        if compat:
            return [("minimal", minimal)]
        return [("a1111", a1111), ("sdcpp-safe", sdcpp_safe), ("minimal", minimal)]

    def get_api_endpoint(self):
        return "http://127.0.0.1:8082/sdapi/v1/txt2img"

    def get_health_endpoint(self):
        return "http://127.0.0.1:8082"
