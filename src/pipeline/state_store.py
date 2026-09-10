"""
Persists PipelineState to/from disk. Swap this implementation (sqlite,
redis, a DB row) without touching models, stages, or the engine —
everything else only depends on the load()/save() contract.

There is exactly one state file: every run appends its own PipelineRun
(including the files it discovered) to state.runs, so a single
state.json holds the full history.
"""
from __future__ import annotations

import os
from pathlib import Path

from src.models.pipeline_context import PipelineState

_SUPPORTED_VERSION = 1


def _ensure_supported_version(state: PipelineState) -> PipelineState:
    if state.version != _SUPPORTED_VERSION:
        raise ValueError(
            f"unsupported state version {state.version}, expected "
            f"{_SUPPORTED_VERSION}"
        )
    return state


class StateStore:
    def __init__(self, state_path: str | Path):
        self.state_path = Path(state_path)

    def has_state(self) -> bool:
        return self.state_path.exists()

    def load(self) -> PipelineState:
        if not self.state_path.exists():
            return PipelineState()
        raw = self.state_path.read_text(encoding="utf-8")
        return _ensure_supported_version(PipelineState.model_validate_json(raw))

    def save(self, state: PipelineState) -> None:
        path = self.state_path
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(state.model_dump_json(indent=2), encoding="utf-8")
        os.replace(tmp, path)