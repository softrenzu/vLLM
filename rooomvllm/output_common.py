from __future__ import annotations

import json
from typing import Any

from .driver import DriverResponse


def usage(output: Any) -> dict[str, int]:
    prompt_tokens = len(getattr(output, "prompt_token_ids", None) or [])
    completion_tokens = sum(
        len(getattr(item, "token_ids", None) or [])
        for item in (getattr(output, "outputs", None) or [])
    )
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
    }


def json_response(payload: dict[str, Any], status: int = 200) -> DriverResponse:
    return DriverResponse(
        status,
        json.dumps(payload).encode("utf-8"),
        {"content-type": "application/json"},
    )
