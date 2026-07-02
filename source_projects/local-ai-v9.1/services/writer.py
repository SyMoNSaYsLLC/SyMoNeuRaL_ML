class WriterService:
    name = "qwen-code"
    kind = "text"

    def format_request(self, data):
        prompt = (data.get("prompt") or "").strip()
        system_prompt = (
            data.get("system_prompt")
            or "You are SyMoNeuRaL Code Writer powered by Qwen Coder. Return practical code, commands, paths, and concise explanations."
        ).strip()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return {
            "messages": messages,
            "stream": True,
            "temperature": float(data.get("temperature", 0.2)),
            "top_p": float(data.get("top_p", 0.95)),
            "max_tokens": int(data.get("max_tokens", 1000)),
        }

    def get_api_endpoint(self):
        return "http://127.0.0.1:8081/v1/chat/completions"

    def get_health_endpoint(self):
        return "http://127.0.0.1:8081/health"
