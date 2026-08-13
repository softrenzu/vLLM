from __future__ import annotations

import time
from typing import Any

from .driver import DriverResponse
from .output_common import json_response, usage


def completion(output: Any, model: str, request_id: str) -> DriverResponse:
    return json_response({
        "id": f"cmpl-{request_id}",
        "object": "text_completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {"index": i, "text": item.text, "finish_reason": getattr(item, "finish_reason", None)}
            for i, item in enumerate(output.outputs)
        ],
        "usage": usage(output),
    })


def chat(output: Any, model: str, request_id: str) -> DriverResponse:
    item = output.outputs[0]
    return json_response({
        "id": f"chatcmpl-{request_id}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": str(item.text)},
            "finish_reason": getattr(item, "finish_reason", None),
        }],
        "usage": usage(output),
    })
