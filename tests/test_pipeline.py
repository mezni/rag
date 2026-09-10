from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.models.pipeline_context import (
    FileRecord,
    FileStatus,
    PipelineContext,
    PipelineState,
)
from src.pipeline.pipeline import Pipeline
from src.pipeline.stage import Stage
from src.pipeline.state_store import StateStore


def _ts() -> datetime:
    return datetime.now(timezone.utc)


def _make_file(path: str = "a.md") -> FileRecord:
    return FileRecord(
        path=path,
        absolute_path=f"/tmp/{path}",
        size_bytes=3,
        hash="abc",
        mtime=1.0,
        first_seen_at=_ts(),
        last_seen_at=_ts(),
    )


class RecordingStage(Stage):
    def __init__(self, name: str = "record"):
        self.name = name

    def run(self, context: PipelineContext) -> PipelineContext:
        context.run.files_scanned = 1
        context.run.files_new = 1
        context.run.files_sent_downstream = 1
        context.state.files["a.md"] = _make_file()
        context.files_to_process = [context.state.files["a.md"]]
        return context


class FailingStage(Stage):
    name = "fail"

    def run(self, context: PipelineContext) -> PipelineContext:
        raise RuntimeError("boom")


class LosingStage(Stage):
    name = "lose"

    def run(self, context: PipelineContext) -> PipelineContext:
        return None


class SwappingStage(Stage):
    name = "swap"

    def run(self, context: PipelineContext) -> PipelineContext:
        context.state = PipelineState()
        return context


def _make_pipeline(tmp_path, stages, **kwargs) -> Pipeline:
    return Pipeline(
        stages=stages,
        state_store=StateStore(tmp_path / "state.json"),
        **kwargs,
    )


def test_rejects_empty_stages(tmp_path) -> None:
    with pytest.raises(ValidationError, match="at least one stage"):
        _make_pipeline(tmp_path, [])


def test_rejects_duplicate_stage_names(tmp_path) -> None:
    with pytest.raises(ValidationError, match="must be unique"):
        _make_pipeline(
            tmp_path,
            [RecordingStage(name="record"), RecordingStage(name="record")],
        )


def test_run_persists_state_and_counts(tmp_path) -> None:
    pipeline = _make_pipeline(tmp_path, [RecordingStage()])
    ctx = pipeline.run("/tmp/in")

    assert ctx.run.files_scanned == 1
    assert ctx.run.finished_at is not None
    assert ctx.run.failed is False

    state = pipeline.state_store.load()
    assert "a.md" in state.files
    assert state.files["a.md"].status is FileStatus.NEW
    assert state.last_run().run_id == ctx.run.run_id


def test_run_records_stage_timing(tmp_path) -> None:
    pipeline = _make_pipeline(tmp_path, [RecordingStage()])
    ctx = pipeline.run("/tmp/in")
    assert "record" in ctx.run.stage_timings_seconds
    assert ctx.run.stage_timings_seconds["record"] >= 0.0


def test_failed_stage_persists_failed_run_and_reraised(tmp_path) -> None:
    pipeline = _make_pipeline(tmp_path, [FailingStage()])
    with pytest.raises(RuntimeError, match="boom"):
        pipeline.run("/tmp/in")
    state = pipeline.state_store.load()
    assert state.last_run().failed is True
    assert state.last_run().finished_at is not None


def test_stage_returning_none_is_rejected(tmp_path) -> None:
    pipeline = _make_pipeline(tmp_path, [LosingStage()])
    with pytest.raises(TypeError, match="expected PipelineContext"):
        pipeline.run("/tmp/in")


def test_max_runs_trims_old_runs(tmp_path) -> None:
    pipeline = _make_pipeline(tmp_path, [RecordingStage()], max_runs=2)
    for _ in range(3):
        pipeline.run("/tmp/in")
    state = pipeline.state_store.load()
    assert len(state.runs) == 2


def test_stage_replacing_state_raises_and_preserves_original(tmp_path) -> None:
    pipeline = _make_pipeline(tmp_path, [SwappingStage()])
    with pytest.raises(RuntimeError, match="replaced PipelineContext.state"):
        pipeline.run("/tmp/in")
    state = pipeline.state_store.load()
    assert state.last_run().failed is True


def test_state_store_round_trip(tmp_path) -> None:
    store = StateStore(tmp_path / "state.json")
    pipeline = _make_pipeline(tmp_path, [RecordingStage()])
    pipeline.run("/tmp/in")
    loaded = store.load()
    assert loaded.files["a.md"].size_bytes == 3
    assert loaded.last_run() is not None


def test_state_store_load_default_for_missing_file(tmp_path) -> None:
    store = StateStore(tmp_path / "missing.json")
    state = store.load()
    assert state.version == 1
    assert state.runs == []