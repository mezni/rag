from datetime import UTC, datetime

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
    return datetime.now(UTC)


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
        context.run.files["a.md"] = _make_file()
        context.files_to_process = [context.run.files["a.md"]]
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
    assert "a.md" in state.last_run().files
    assert state.last_run().files["a.md"].status is FileStatus.NEW
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
    assert loaded.last_run().files["a.md"].size_bytes == 3
    assert loaded.last_run() is not None


def test_state_store_load_default_for_missing_file(tmp_path) -> None:
    store = StateStore(tmp_path / "missing.json")
    state = store.load()
    assert state.version == 1
    assert state.runs == []


def test_runs_each_snapshot_their_files(tmp_path) -> None:
    pipeline = _make_pipeline(tmp_path, [RecordingStage()])
    first = pipeline.run("/tmp/in")
    second = pipeline.run("/tmp/in")

    assert first.run.files["a.md"].status is FileStatus.NEW
    assert second.run.files["a.md"].status is FileStatus.NEW
    store = pipeline.state_store
    assert store.has_state() is True
    runs = store.load().runs
    assert [r.run_id for r in runs] == [first.run.run_id, second.run.run_id]
    assert "a.md" in runs[0].files
    assert "a.md" in runs[1].files
    assert not store.state_path.with_name("state_last.json").exists()


class DeleteCycleStage(Stage):
    name = "cycle"

    def __init__(self) -> None:
        self.n = 0

    def run(self, context: PipelineContext) -> PipelineContext:
        self.n += 1
        record = _make_file()
        if self.n == 1:
            record.status = FileStatus.NEW
        else:
            record.status = FileStatus.DELETED
        context.run.files["a.md"] = record
        context.files_to_process = [] if self.n == 2 else [record]
        return context


def test_deleted_files_have_artifacts_removed(tmp_path) -> None:
    processed = tmp_path / "processed"
    processed.mkdir(parents=True, exist_ok=True)
    (processed / "a.txt").write_text("old content", encoding="utf-8")
    (processed / "a.v1.txt").write_text("older content", encoding="utf-8")
    (processed / "a.md").write_text("old content", encoding="utf-8")
    (processed / "a.v1.md").write_text("older content", encoding="utf-8")
    assert (processed / "a.txt").exists()
    assert (processed / "a.md").exists()

    state_path = tmp_path / "state.json"
    pipeline = Pipeline(
        stages=[DeleteCycleStage()],
        state_store=StateStore(state_path),
    )
    pipeline.run("/tmp/in", output_dir=str(processed))

    assert not state_path.with_name("state_last.json").exists()

    pipeline.run("/tmp/in", output_dir=str(processed))

    store = pipeline.state_store.load()
    assert store.last_run().files["a.md"].status is FileStatus.DELETED
    assert not (processed / "a.txt").exists()
    assert not (processed / "a.v1.txt").exists()
    assert not (processed / "a.md").exists()
    assert not (processed / "a.v1.md").exists()
