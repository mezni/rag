from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.models.pipeline_context import (
    FileRecord,
    FileStatus,
    PipelineContext,
    PipelineRun,
    PipelineState,
)


def _ts() -> datetime:
    return datetime.now(timezone.utc)


def _make_file(**overrides) -> FileRecord:
    base = {
        "path": "a.md",
        "absolute_path": "/tmp/a.md",
        "size_bytes": 3,
        "hash": "abc",
        "mtime": 1.0,
        "first_seen_at": _ts(),
        "last_seen_at": _ts(),
    }
    base.update(overrides)
    return FileRecord(**base)


def _make_run(run_id: str = "r1") -> PipelineRun:
    return PipelineRun(run_id=run_id, started_at=_ts(), input_dir="/tmp/in")


def test_file_status_values() -> None:
    assert [s.value for s in FileStatus] == [
        "new",
        "updated",
        "unchanged",
        "deleted",
    ]


def test_file_record_defaults() -> None:
    rec = _make_file()
    assert rec.status is FileStatus.NEW
    assert rec.last_processed_at is None
    assert rec.stage_outputs == {}


def test_file_record_requires_core_fields() -> None:
    with pytest.raises(ValidationError):
        FileRecord(path="a.md")


def test_pipeline_state_defaults() -> None:
    state = PipelineState()
    assert state.version == 1
    assert state.runs == []
    assert state.last_run() is None


def test_pipeline_state_last_run() -> None:
    state = PipelineState()
    state.runs = [_make_run("r1")]
    assert state.last_run() is not None
    assert state.last_run().run_id == "r1"


def test_pipeline_run_defaults() -> None:
    run = _make_run()
    assert run.finished_at is None
    assert run.failed is False
    assert run.files_scanned == 0
    assert run.files == {}
    assert run.stage_timings_seconds == {}


def test_pipeline_context_defaults() -> None:
    ctx = PipelineContext(state=PipelineState(), run=_make_run())
    assert ctx.files_to_process == []
    assert ctx.scratch == {}


def test_pipeline_context_validates_assignment() -> None:
    ctx = PipelineContext(state=PipelineState(), run=_make_run())
    with pytest.raises(ValidationError):
        ctx.files_to_process = "not a list"