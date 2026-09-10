from pathlib import Path

import pytest

from src.ingestion.loader import Loader, LoaderResult
from src.models.pipeline_context import FileStatus


def _write(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_first_run_marks_everything_new(tmp_path: Path) -> None:
    _write(tmp_path, "a.md", "hello")
    _write(tmp_path, "b.txt", "world")

    result = Loader(input_dir=tmp_path).run({})

    assert result.scanned == 2
    assert result.new == 2
    assert result.updated == 0
    assert result.unchanged == 0
    assert result.deleted == 0
    assert sorted(f.path for f in result.files_to_process) == ["a.md", "b.txt"]
    assert result.files["a.md"].status is FileStatus.NEW
    assert result.files["a.md"].absolute_path == str(tmp_path / "a.md")
    assert result.files["a.md"].hash


def test_unchanged_file_stays_unchanged(tmp_path: Path) -> None:
    _write(tmp_path, "a.md", "hello")
    first = Loader(input_dir=tmp_path).run({})

    result = Loader(input_dir=tmp_path).run(first.files)

    assert result.files_to_process == []
    assert result.unchanged == 1
    assert result.new == 0
    assert result.files["a.md"].status is FileStatus.UNCHANGED


def test_changed_file_becomes_updated(tmp_path: Path) -> None:
    _write(tmp_path, "a.md", "hello")
    first = Loader(input_dir=tmp_path).run({})
    old_hash = first.files["a.md"].hash

    _write(tmp_path, "a.md", "hello changed")
    second = Loader(input_dir=tmp_path).run(first.files)

    record = second.files["a.md"]
    assert record.status is FileStatus.UPDATED
    assert second.updated == 1
    assert second.new == 0
    assert record.hash != old_hash
    assert [f.path for f in second.files_to_process] == ["a.md"]


def test_missing_file_marked_deleted(tmp_path: Path) -> None:
    path = _write(tmp_path, "a.md", "hello")
    first = Loader(input_dir=tmp_path).run({})

    path.unlink()
    result = Loader(input_dir=tmp_path).run(first.files)

    assert result.files["a.md"].status is FileStatus.DELETED
    assert result.deleted == 1
    assert result.scanned == 0


def test_second_run_processes_only_new(tmp_path: Path) -> None:
    _write(tmp_path, "a.md", "hello")
    first = Loader(input_dir=tmp_path).run({})

    _write(tmp_path, "b.md", "new")
    result = Loader(input_dir=tmp_path).run(first.files)

    assert sorted(f.path for f in result.files_to_process) == ["b.md"]
    assert result.files["b.md"].status is FileStatus.NEW
    assert result.files["a.md"].status is FileStatus.UNCHANGED


def test_glob_pattern_limits_scan(tmp_path: Path) -> None:
    _write(tmp_path, "a.md", "hello")
    _write(tmp_path, "b.txt", "world")

    result = Loader(input_dir=tmp_path, glob_pattern="*.md").run({})

    assert result.scanned == 1
    assert sorted(result.files) == ["a.md"]


def test_directories_are_not_counted_as_files(tmp_path: Path) -> None:
    _write(tmp_path / "sub", "a.md", "hello")

    result = Loader(input_dir=tmp_path).run({})

    assert result.scanned == 1
    assert "sub/a.md" in result.files


def test_missing_input_dir_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="does not exist"):
        Loader(input_dir=tmp_path / "nope").run({})


def test_previous_run_snapshot_is_not_mutated(tmp_path: Path) -> None:
    _write(tmp_path, "a.md", "hello")
    first = Loader(input_dir=tmp_path).run({})
    previous = first.files["a.md"]

    _write(tmp_path, "a.md", "hello changed")
    second = Loader(input_dir=tmp_path).run(first.files)

    assert previous.hash != second.files["a.md"].hash
    assert first.files["a.md"].status is FileStatus.NEW
    assert second.files["a.md"].status is FileStatus.UPDATED


def test_loader_result_defaults(tmp_path: Path) -> None:
    result = LoaderResult(files_to_process=[], files={})
    assert result.scanned == 0
    assert result.new == 0
    assert result.updated == 0
    assert result.unchanged == 0
    assert result.deleted == 0


def test_loader_creates_missing_dirs_without_copying_files(tmp_path: Path) -> None:
    _write(tmp_path / "raw", "a.md", "hello")
    _write(tmp_path / "raw" / "sub", "dir/b.txt", "world")
    output = tmp_path / "processed"

    Loader(
        input_dir=tmp_path / "raw",
        output_dir=output,
    ).run({})

    assert (output / "sub" / "dir").is_dir()
    assert not (output / "a.md").exists()
    assert not (output / "sub" / "dir" / "b.txt").exists()


def test_loader_does_not_copy_without_output_dir(tmp_path: Path) -> None:
    _write(tmp_path, "a.md", "hello")
    output = tmp_path / "processed"

    Loader(input_dir=tmp_path).run({})

    assert not output.exists()
