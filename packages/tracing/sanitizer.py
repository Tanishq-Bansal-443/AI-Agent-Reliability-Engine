"""
Secret and sensitive data sanitizer module for the AI Agent Reliability Engine.

Provides functions to redact API keys, credentials, tokens, passwords, and sensitive
metadata fields from traces, error messages, and artifacts.
"""

from __future__ import annotations

import re
from typing import Any

_SENSITIVE_KEY_SUBSTRINGS: set[str] = {
    "password",
    "passwd",
    "secret",
    "api_key",
    "apikey",
    "token",
    "access_token",
    "auth_token",
    "authorization",
    "private_key",
    "credential",
    "db_password",
}

REDACTED_PLACEHOLDER = "[REDACTED_SECRET]"


def sanitize_string(text: str) -> str:
    """
    Sanitize sensitive secret patterns from a string.
    """
    if not text or not isinstance(text, str):
        return text

    result = text
    # 1. Check known regex patterns
    # OpenAI / generic sk- keys
    result = re.sub(r"sk-[a-zA-Z0-9_-]{20,}", REDACTED_PLACEHOLDER, result)
    # Google AIza keys
    result = re.sub(r"AIza[0-9A-Za-z\-_]{35}", REDACTED_PLACEHOLDER, result)
    # AWS AKIA keys
    result = re.sub(r"AKIA[0-9A-Z]{16}", REDACTED_PLACEHOLDER, result)
    # Bearer tokens
    result = re.sub(r"Bearer\s+[a-zA-Z0-9_\-\.=]+", f"Bearer {REDACTED_PLACEHOLDER}", result, flags=re.IGNORECASE)
    # Database URIs
    result = re.sub(r"([a-zA-Z0-9\+]+://[^:]+:)[^@]+(@[^/]+/.+)", f"\\1{REDACTED_PLACEHOLDER}\\2", result)
    # Key-value pairs
    result = re.sub(
        r"(?i)\b(password|passwd|api_key|apikey|secret|access_token|auth_token|private_key)\b\s*([:=])\s*[\"']?[^\s\"',;]+[\"']?",
        rf"\1\2 {REDACTED_PLACEHOLDER}",
        result,
    )

    return result


def sanitize_data(data: Any) -> Any:
    """
    Recursively sanitize structured data (dicts, lists, primitives).
    Redacts dictionary values where the key matches sensitive key terms,
    and runs string sanitization on string values.
    """
    if isinstance(data, dict):
        sanitized_dict = {}
        for key, value in data.items():
            key_str = str(key).lower()
            if any(sens in key_str for sens in _SENSITIVE_KEY_SUBSTRINGS):
                sanitized_dict[key] = REDACTED_PLACEHOLDER
            else:
                sanitized_dict[key] = sanitize_data(value)
        return sanitized_dict
    elif isinstance(data, list):
        return [sanitize_data(item) for item in data]
    elif isinstance(data, tuple):
        return tuple(sanitize_data(item) for item in data)
    elif isinstance(data, str):
        return sanitize_string(data)
    else:
        return data


class SecretSanitizer:
    """
    Class wrapper for secret sanitization utilities.
    """

    @staticmethod
    def sanitize_string(text: str) -> str:
        return sanitize_string(text)

    @staticmethod
    def sanitize_data(data: Any) -> Any:
        return sanitize_data(data)
