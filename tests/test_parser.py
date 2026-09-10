from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.ingestion.parser import (
    ParseError,
    Parser,
    UnsupportedFormatError,
    is_supported,
    parse_file,
)
from src.models.pipeline_context import FileRecord


def _build_pdf(path: Path, text: str = "Hello PDF") -> Path:
    stream = b"BT /F1 24 Tf 100 700 Td (" + text.encode() + b") Tj ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length "
        + str(len(stream)).encode()
        + b" >>\nstream\n"
        + stream
        + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{index} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode() + b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n"
        + str(xref).encode()
        + b"\n%%EOF\n"
    )
    path.write_bytes(bytes(out))
    return path


def _make_record(path: Path) -> FileRecord:
    return FileRecord(
        path=path.name,
        absolute_path=str(path),
        size_bytes=path.stat().st_size,
        hash="unused",
        mtime=1.0,
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )


def test_is_supported_pdf_only(tmp_path: Path) -> None:
    assert is_supported(tmp_path / "doc.pdf") is True
    assert is_supported(tmp_path / "doc.md") is False
    assert is_supported(tmp_path / "doc.txt") is False


def test_parse_pdf_returns_text(tmp_path: Path) -> None:
    path = _build_pdf(tmp_path / "doc.pdf")
    assert "Hello PDF" in parse_file(path)


def test_parse_unsupported_extension_raises(tmp_path: Path) -> None:
    path = tmp_path / "doc.md"
    path.write_text("hi", encoding="utf-8")
    with pytest.raises(UnsupportedFormatError):
        parse_file(path)


def test_parse_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ParseError):
        parse_file(tmp_path / "missing.pdf")


def test_parser_parse_one_writes_content(tmp_path: Path) -> None:
    path = _build_pdf(tmp_path / "doc.pdf")
    record = _make_record(path)

    result = Parser().parse_one(record)

    assert result is record
    assert record.last_processed_at is not None
    assert "Hello PDF" in record.stage_outputs["parser"]["content"]


def test_parser_parse_one_records_error(tmp_path: Path) -> None:
    path = tmp_path / "doc.md"
    path.write_text("hi", encoding="utf-8")
    record = _make_record(path)

    Parser().parse_one(record)

    assert "error" in record.stage_outputs["parser"]


def test_parser_run_processes_all_records(tmp_path: Path) -> None:
    first = _build_pdf(tmp_path / "a.pdf")
    second = _build_pdf(tmp_path / "b.pdf")

    records = Parser().run([_make_record(first), _make_record(second)])

    assert len(records) == 2
    assert all("content" in record.stage_outputs["parser"] for record in records)