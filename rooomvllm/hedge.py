from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from .driver import DriverResponse
from .runtime import BackendRuntime

if TYPE_CHECKING:
    from .gateway import Gateway


async def hedge_first_two(
    gateway: "Gateway",
    path: str,
    body: dict[str, Any],
    candidates,
    request_id: str,
) -> tuple[DriverResponse | None, BackendRuntime | None, list]:
    (first_rt, first_model, _), (second_rt, second_model, _) = candidates[:2]
    first = asyncio.create_task(
        gateway.send(path, body, first_rt, first_model, request_id)
    )
    done, _ = await asyncio.wait(
        {first}, timeout=gateway.config.routing.hedge_delay_ms / 1000
    )
    if done:
        try:
            result = first.result()
            if result.status_code < 500 and result.status_code != 429:
                return result, first_rt, candidates[1:]
        except Exception:
            pass
        return None, None, candidates[1:]

    second = asyncio.create_task(
        gateway.send(path, body, second_rt, second_model, request_id)
    )
    pending = {first, second}
    result = None
    used = None
    while pending and result is None:
        finished, pending = await asyncio.wait(
            pending, return_when=asyncio.FIRST_COMPLETED
        )
        for task in finished:
            try:
                value = task.result()
                if value.status_code < 500 and value.status_code != 429:
                    result = value
                    used = first_rt if task is first else second_rt
                    break
            except Exception:
                pass
    for task in pending:
        task.cancel()
    await asyncio.gather(*pending, return_exceptions=True)
    return result, used, candidates[2:]
