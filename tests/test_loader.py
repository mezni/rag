from pathlib import Path

import pytest

from src.ingestion.loader import Loader, LoaderResult
from src.models.pipeline_context import FileStatus, PipelineState


def _write(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_first_run_marks_everything_new(tmp_path: Path) -> None:
    _write(tmp_path, "a.md", "hello")
    _write(tmp_path, "b.txt", "world")
    state = PipelineState()

    result = Loader(input_dir=tmp_path).run(state)

    assert result.scanned == 2
    assert result.new == 2
    assert result.updated == 0
    assert result.unchanged == 0
    assert result.deleted == 0
    assert result.state is state
    assert sorted(f.path for f in result.files_to_process) == ["a.md", "b.txt"]
    assert state.files["a.md"].status is FileStatus.NEW
    assert state.files["a.md"].absolute_path == str(tmp_path / "a.md")
    assert state.files["a.md"].hash


def test_unchanged_file_stays_unchanged(tmp_path: Path) -> None:
    _write(tmp_path, "a.md", "hello")
    state = PipelineState()
    Loader(input_dir=tmp_path).run(state)

    result = Loader(input_dir=tmp_path).run(state)

    assert result.files_to_process == []
    assert result.unchanged == 1
    assert result.new == 0
    assert state.files["a.md"].status is FileStatus.UNCHANGED


def test_changed_file_becomes_updated(tmp_path: Path) -> None:
    _write(tmp_path, "a.md", "hello")
    state = PipelineState()
    Loader(input_dir=tmp_path).run(state)
    old_hash = state.files["a.md"].hash

    _write(tmp_path, "a.md", "hello changed")
    second = Loader(input_dir=tmp_path).run(state)

    record = state.files["a.md"]
    assert record.status is FileStatus.UPDATED
    assert second.updated == 1
    assert second.new == 0
    assert record.hash != old_hash
    assert [f.path for f in second.files_to_process] == ["a.md"]


def test_missing_file_marked_deleted(tmp_path: Path) -> None:
    path = _write(tmp_path, "a.md", "hello")
    state = PipelineState()
    Loader(input_dir=tmp_path).run(state)

    path.unlink()
    result = Loader(input_dir=tmp_path).run(state)

    assert state.files["a.md"].status is FileStatus.DELETED
    assert result.deleted == 1
    assert result.scanned == 0


def test_second_run_processes_only_new(tmp_path: Path) -> None:
    _write(tmp_path, "a.md", "hello")
    state = PipelineState()
    Loader(input_dir=tmp_path).run(state)

    _write(tmp_path, "b.md", "new")
    result = Loader(input_dir=tmp_path).run(state)

    assert sorted(f.path for f in result.files_to_process) == ["b.md"]
    assert state.files["b.md"].status is FileStatus.NEW
    assert state.files["a.md"].status is FileStatus.UNCHANGED


def test_glob_pattern_limits_scan(tmp_path: Path) -> None:
    _write(tmp_path, "a.md", "hello")
    _write(tmp_path, "b.txt", "world")
    state = PipelineState()

    result = Loader(input_dir=tmp_path, glob_pattern="*.md").run(state)

    assert result.scanned == 1
    assert sorted(state.files) == ["a.md"]


def test_directories_are_not_counted_as_files(tmp_path: Path) -> None:
    _write(tmp_path / "sub", "a.md", "hello")
    state = PipelineState()

    result = Loader(input_dir=tmp_path).run(state)

    assert result.scanned == 1
    assert "sub/a.md" in state.files


def test_missing_input_dir_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="does not exist"):
        Loader(input_dir=tmp_path / "nope").run(PipelineState())


def test_loader_result_keeps_state_identity(tmp_path: Path) -> None:
    _write(tmp_path, "a.md", "hello")
    state = PipelineState()
    result = Loader(input_dir=tmp_path).run(state)
    assert result.state is state


def test_loader_result_defaults(tmp_path: Path) -> None:
    result = LoaderResult(files_to_process=[], state=PipelineState())
    assert result.scanned == 0
    assert result.new == 0
    assert result.updated == 0
    assert result.unchanged == 0
    assert result.deleted == 0