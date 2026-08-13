from __future__ import annotations

import os
import uvicorn
from .config import load_config

def main() -> None:
    cfg = load_config(os.getenv("ROOOMVLLM_CONFIG", "config.yaml"))
    uvicorn.run("rooomvllm.app:create_app", factory=True, host=cfg.bind, port=cfg.port)
