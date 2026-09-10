"""
Persists PipelineState to/from disk. Swap this implementation (sqlite,
redis, a DB row) without touching models, stages, or the engine —
everything else only depends on the load()/save() contract.

State is stored in two files:
- state_path holds the state from the most recent run.
- last_path holds a snapshot of the state taken before that run, so
  the engine can diff "what was" against "what is".
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
        self.last_path = self.state_path.with_name(
            self.state_path.stem + "_last" + self.state_path.suffix
        )

    def has_state(self) -> bool:
        return self.state_path.exists()

    def load(self) -> PipelineState:
        if not self.state_path.exists():
            return PipelineState()
        raw = self.state_path.read_text(encoding="utf-8")
        return _ensure_supported_version(PipelineState.model_validate_json(raw))

    def load_last(self) -> PipelineState | None:
        if not self.last_path.exists():
            return None
        raw = self.last_path.read_text(encoding="utf-8")
        return _ensure_supported_version(PipelineState.model_validate_json(raw))

    def save(self, state: PipelineState) -> None:
        self._write(state, self.state_path)

    def save_last(self, state: PipelineState) -> None:
        self._write(state, self.last_path)

    def _write(self, state: PipelineState, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(state.model_dump_json(indent=2), encoding="utf-8")
        os.replace(tmp, path)