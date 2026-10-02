#!/usr/bin/env python3
"""Minimal OpenAI-compatible chat client (stdlib only).

Reads credentials exclusively from environment variables via config.py.
Never prints or persists the API key.
"""

import json
import re
import sys
import urllib.error
import urllib.request

import config


def chat(system_prompt: str, user_prompt: str, max_tokens: int = None) -> str:
    """Call the configured chat-completions endpoint and return text content.

    Raises RuntimeError when the key is missing or the request fails.
    """
    settings = config.llm_settings()
    if not settings["api_key"]:
        raise RuntimeError(
            f"LLM key not configured. Set environment variable "
            f"{config.LLM_API_KEY_ENV} (and optionally {config.LLM_BASE_URL_ENV}, "
            f"{config.LLM_MODEL_ENV})."
        )

    payload = {
        "model": settings["model"],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": max_tokens or config.LLM_MAX_TOKENS,
        "temperature": config.LLM_TEMPERATURE,
    }
    if getattr(config, "LLM_DISABLE_THINKING", False):
        payload["thinking"] = {"type": "disabled"}
    request = urllib.request.Request(
        f"{settings['base_url']}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
    )
    request.add_header("Authorization", f"Bearer {settings['api_key']}")
    request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=config.LLM_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LLM HTTP {exc.code}: {detail[:500]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"LLM network error: {exc.reason}") from exc

    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"unexpected LLM response: {json.dumps(data)[:500]}") from exc


def extract_json_object(text: str) -> dict:
    """Extract the first JSON object from an LLM reply (tolerates prose/code fences)."""
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    start = cleaned.find("{")
    if start == -1:
        raise ValueError("no JSON object found in LLM output")
    depth = 0
    for i in range(start, len(cleaned)):
        if cleaned[i] == "{":
            depth += 1
        elif cleaned[i] == "}":
            depth -= 1
            if depth == 0:
                return json.loads(cleaned[start:i + 1])
    raise ValueError("unbalanced JSON object in LLM output")


def warn(msg: str) -> None:
    print(f"[warn] {msg}", file=sys.stderr)
