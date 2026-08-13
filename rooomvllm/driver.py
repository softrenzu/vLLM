from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .runtime import BackendRuntime


@dataclass
class DriverResponse:
    status_code: int
    content: bytes
    headers: dict[str, str]


class InferenceDriver(Protocol):
    async def infer(
        self,
        backend: BackendRuntime,
        path: str,
        body: dict[str, Any],
        request_id: str,
    ) -> DriverResponse: ...
