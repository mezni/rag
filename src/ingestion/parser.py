"""
Pure domain logic for turning files into raw text. No Stage or
pipeline-context imports here — keeps this module unit-testable on
its own.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from llama_index.core import SimpleDirectoryReader
from llama_index.readers.file import PDFReader

from src.config.logger import get_logger
from src.models.pipeline_context import FileRecord

logger = get_logger(__name__)

SUPPORTED_EXTENSIONS = {".pdf"}


class UnsupportedFormatError(Exception):
    """Raised when parse_file is called on an extension we cannot read."""


class ParseError(Exception):
    """Raised when a supported file cannot be parsed."""


def is_supported(path: str | Path) -> bool:
    return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS


def parse_file(path: str | Path) -> str:
    file = Path(path)
    if not is_supported(file):
        raise UnsupportedFormatError(f"unsupported extension: {file.suffix}")
    try:
        documents = SimpleDirectoryReader(
            input_files=[str(file)],
            file_extractor={".pdf": PDFReader()},
        ).load_data()
    except Exception as exc:
        raise ParseError(f"could not parse {file}: {exc}") from exc
    return "\n\n".join(document.text or "" for document in documents)


class Parser:
    def __init__(self, output_dir: str | Path | None = None):
        self.output_dir = Path(output_dir) if output_dir else None

    def parse_one(self, record: FileRecord) -> FileRecord:
        record.last_processed_at = datetime.now(timezone.utc)
        try:
            content = parse_file(record.absolute_path)
        except (UnsupportedFormatError, ParseError) as exc:
            logger.warning(f"parser: skipped {record.path}: {exc}")
            record.stage_outputs["parser"] = {"error": str(exc)}
            return record
        output = {"content": content}
        if self.output_dir is not None and content.strip():
            rel = Path(record.path)
            dest = self.output_dir / rel.parent / f"{rel.stem}.md"
            dest.parent.mkdir(parents=True, exist_ok=True)
            self._write_versioned(dest, content, output)
        record.stage_outputs["parser"] = output
        return record

    @staticmethod
    def _write_versioned(dest: Path, content: str, output: dict) -> None:
        old = dest.read_text(encoding="utf-8") if dest.exists() else None
        if old is not None and old != content:
            version = dest.with_name(f"{dest.stem}.v1.md")
            index = 1
            while version.exists():
                index += 1
                version = dest.with_name(f"{dest.stem}.v{index}.md")
            version.write_text(old, encoding="utf-8")
            output["previous_version"] = str(version)
        dest.write_text(content, encoding="utf-8")
        output["processed_path"] = str(dest)

    def run(self, records: list[FileRecord]) -> list[FileRecord]:
        return [self.parse_one(r) for r in records]