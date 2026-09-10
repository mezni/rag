from datetime import datetime, timezone
from pathlib import Path

from src.ingestion.cleaner import Cleaner, CleanerResult, normalize_newlines
from src.models.pipeline_context import FileRecord


def _make_record(path: str, processed_path: str | None) -> FileRecord:
    record = FileRecord(
        path=path,
        absolute_path=f"/tmp/{path}",
        size_bytes=3,
        hash="abc",
        mtime=1.0,
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )
    record.stage_outputs["parser"] = {"processed_path": processed_path} if processed_path else {}
    return record


def test_normalize_newlines_collapses_but_keeps_single() -> None:
    assert normalize_newlines("a\n\n\nb") == "a\nb"
    assert normalize_newlines("a\nb") == "a\nb"
    assert normalize_newlines("\n\n") == "\n"
    assert normalize_newlines("") == ""


def test_cleaner_rewrites_parser_output(tmp_path: Path) -> None:
    out = tmp_path / "processed.md"
    out.write_text("line1\n\n\n\nline2\n\nline3", encoding="utf-8")

    result = Cleaner().run([_make_record("doc/a.pdf", str(out))])

    assert out.read_text(encoding="utf-8") == "line1\nline2\nline3"
    assert result.cleaned == 1


def test_cleaner_skips_already_clean_and_missing(tmp_path: Path) -> None:
    clean_file = tmp_path / "clean.md"
    clean_file.write_text("only\none", encoding="utf-8")

    result = Cleaner().run(
        [
            _make_record("a.pdf", str(clean_file)),
            _make_record("b.pdf", str(tmp_path / "missing.md")),
            _make_record("c.pdf", None),
        ]
    )

    assert result.cleaned == 0
    assert clean_file.read_text(encoding="utf-8") == "only\none"


def test_cleaner_result_default() -> None:
    assert CleanerResult().cleaned == 0