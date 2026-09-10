from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.ingestion.cleaner import Cleaner, CleanerResult, to_markdown
from src.models.pipeline_context import FileRecord


def _make_record(path: str, processed_path: str | None, version: int = 1) -> FileRecord:
    record = FileRecord(
        path=path,
        absolute_path=f"/tmp/{path}",
        size_bytes=3,
        hash="abc",
        mtime=1.0,
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
        version=version,
    )
    record.stage_outputs["parser"] = {"processed_path": processed_path} if processed_path else {}
    return record


def test_cleaner_converts_txt_to_markdown_in_same_dir(tmp_path: Path) -> None:
    txt = tmp_path / "doc.txt"
    txt.write_text("# Hello\n\ntext line", encoding="utf-8")

    result = Cleaner().run([_make_record("doc/a.pdf", str(txt))])

    md = tmp_path / "doc.md"
    assert md.exists()
    assert "Hello" in md.read_text(encoding="utf-8")
    assert result.cleaned == 1


def test_cleaner_converts_html_tags_to_markdown(tmp_path: Path) -> None:
    txt = tmp_path / "doc.txt"
    txt.write_text("Title\n<b>Document ID</b>\nAW-LEG-011", encoding="utf-8")

    Cleaner().run([_make_record("doc.pdf", str(txt))])

    md = tmp_path / "doc.md"
    output = md.read_text(encoding="utf-8")
    assert "<b>" not in output
    assert "**Document ID**" in output


def test_cleaner_records_version(tmp_path: Path) -> None:
    txt = tmp_path / "doc.txt"
    txt.write_text("hello", encoding="utf-8")

    record = _make_record("doc/a.pdf", str(txt), version=3)
    Cleaner().run([record])

    assert record.stage_outputs["cleaner"]["version"] == 3


def test_cleaner_skips_missing_txt_and_no_path(tmp_path: Path) -> None:
    result = Cleaner().run(
        [
            _make_record("a.pdf", str(tmp_path / "missing.txt")),
            _make_record("b.pdf", None),
        ]
    )

    assert result.cleaned == 0


class _FailingConverter:
    def convert_stream(self, stream, file_extension: str):
        raise RuntimeError("boom")


def test_cleaner_skips_unconvertible(tmp_path: Path, monkeypatch) -> None:
    import src.ingestion.cleaner as cleaner_mod

    monkeypatch.setattr(cleaner_mod, "_markitdown", _FailingConverter())
    txt = tmp_path / "doc.txt"
    txt.write_text("hello", encoding="utf-8")

    result = Cleaner().run([_make_record("doc.pdf", str(txt))])

    assert result.cleaned == 0
    assert not (tmp_path / "doc.md").exists()


def test_to_markdown_returns_none_on_failure(tmp_path: Path, monkeypatch) -> None:
    import src.ingestion.cleaner as cleaner_mod

    monkeypatch.setattr(cleaner_mod, "_markitdown", _FailingConverter())
    txt = tmp_path / "doc.txt"
    txt.write_text("x", encoding="utf-8")
    assert to_markdown(txt) is None


def test_cleaner_result_default() -> None:
    assert CleanerResult().cleaned == 0