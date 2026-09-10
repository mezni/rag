"""
Persists PipelineState to/from disk. Swap this implementation (sqlite,
redis, a DB row) without touching models, stages, or the engine —
everything else only depends on the load()/save() contract.
"""
from __future__ import annotations

import os
from pathlib import Path

from src.models.pipeline_context import PipelineState

_SUPPORTED_VERSION = 1


class StateStore:
    def __init__(self, state_path: str | Path):
        self.state_path = Path(state_path)

    def load(self) -> PipelineState:
        if not self.state_path.exists():
            return PipelineState()
        raw = self.state_path.read_text(encoding="utf-8")
        state = PipelineState.model_validate_json(raw)
        if state.version != _SUPPORTED_VERSION:
            raise ValueError(
                f"unsupported state version {state.version}, expected "
                f"{_SUPPORTED_VERSION}"
            )
        return state

    def save(self, state: PipelineState) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        tmp.write_text(state.model_dump_json(indent=2), encoding="utf-8")
        os.replace(tmp, self.state_path)