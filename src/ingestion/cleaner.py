"""
Pure domain logic for cleaning parser output files. The cleaner runs
markitdown over each parser artifact (.txt) and writes the resulting
markdown (.md) in the same directory. No Stage or pipeline-context
imports.
"""

from __future__ import annotations

import io
from pathlib import Path

from markitdown import MarkItDown
from pydantic import BaseModel

from src.config.logger import get_logger
from src.models.pipeline_context import FileRecord

logger = get_logger(__name__)

_markitdown = MarkItDown()


def to_markdown(txt: Path) -> str | None:
    """Convert a text file to markdown via markitdown. None on failure.

    The extracted text is HTML-ish (bold labels come out as <b>…</b>),
    so it is fed to markitdown as HTML: tags become real markdown
    (**…**) instead of leaking through literally.
    """
    try:
        text = txt.read_text(encoding="utf-8")
        doc = _markitdown.convert_stream(
            io.BytesIO(text.encode("utf-8")), file_extension=".html"
        )
        return doc.text_content
    except Exception as exc:
        logger.warning(f"cleaner: markitdown failed for {txt}: {exc}")
        return None


class CleanerResult(BaseModel):
    cleaned: int = 0


class Cleaner:
    def run(self, records: list[FileRecord]) -> CleanerResult:
        result = CleanerResult()
        for record in records:
            path = record.stage_outputs.get("parser", {}).get("processed_path")
            if not path:
                continue
            txt = Path(path)
            if not txt.exists():
                continue
            content = to_markdown(txt)
            if content is None:
                continue
            md = txt.with_suffix(".md")
            md.write_text(content, encoding="utf-8")
            record.stage_outputs["cleaner"] = {"version": record.version}
            result.cleaned += 1
            logger.info(f"cleaner: converted {txt} -> {md}")
        return result
