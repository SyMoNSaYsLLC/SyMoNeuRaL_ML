class GemmaService:
    name = "gemma-writer"
    kind = "text"

    def format_request(self, data):
        prompt = (data.get("prompt") or "").strip()
        system_prompt = (
            data.get("system_prompt")
            or "You are SyMoNeuRaL Gemma Writer. Write, rewrite, edit, summarize, and draft clean text. Be direct, useful, and do not add model chatter."
        ).strip()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return {
            "messages": messages,
            "stream": True,
            "temperature": float(data.get("temperature", 0.65)),
            "top_p": float(data.get("top_p", 0.95)),
            "max_tokens": int(data.get("max_tokens", 700)),
        }

    def get_api_endpoint(self):
        return "http://127.0.0.1:8080/v1/chat/completions"

    def get_health_endpoint(self):
        return "http://127.0.0.1:8080/health"
