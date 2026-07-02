from __future__ import annotations

import json
from typing import AsyncIterator

import httpx


async def stream_chat_completion(endpoint: str, payload: dict) -> AsyncIterator[bytes]:
    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream("POST", endpoint, json=payload) as resp:
            if resp.status_code >= 400:
                body = await resp.aread()
                yield f"data: {json.dumps({'error': body.decode('utf-8', 'replace') or resp.reason_phrase})}\n\n".encode()
                return
            async for chunk in resp.aiter_bytes():
                yield chunk


def build_chat_payload(prompt: str, system_prompt: str = "", temperature: float = 0.65, top_p: float = 0.95, max_tokens: int = 700, stream: bool = True) -> dict:
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    return {"messages": messages, "stream": stream, "temperature": temperature, "top_p": top_p, "max_tokens": max_tokens}
