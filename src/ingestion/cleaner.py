"""
Pure domain logic for cleaning parser output files. Currently the only
cleanup is collapsing runs of newlines — more cleanups can be layered
in here later. No Stage or pipeline-context imports.
"""
from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel

from src.config.logger import get_logger
from src.models.pipeline_context import FileRecord

logger = get_logger(__name__)

_MULTI_NEWLINE = re.compile(r"\n{2,}")


def normalize_newlines(text: str) -> str:
    """Collapse runs of multiple newlines into a single newline."""
    return _MULTI_NEWLINE.sub("\n", text)


class CleanerResult(BaseModel):
    cleaned: int = 0


class Cleaner:
    def run(self, records: list[FileRecord]) -> CleanerResult:
        result = CleanerResult()
        for record in records:
            path = record.stage_outputs.get("parser", {}).get("processed_path")
            if not path:
                continue
            file = Path(path)
            if not file.exists():
                continue
            text = file.read_text(encoding="utf-8")
            normalized = normalize_newlines(text)
            if normalized != text:
                file.write_text(normalized, encoding="utf-8")
                result.cleaned += 1
                logger.info(f"cleaner: normalized newlines in {file}")
        return result