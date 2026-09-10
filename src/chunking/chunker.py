"""
Pure domain logic for chunking parser output into fixed-size, sentence-aligned
pieces using llama-index's SentenceSplitter. No Stage or pipeline-context
imports — keeps this module unit-testable on its own.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from llama_index.core.node_parser import SentenceSplitter
from pydantic import BaseModel

from src.config.logger import get_logger
from src.models.pipeline_context import FileRecord

logger = get_logger(__name__)

DEFAULT_CHUNK_SIZE = 512
DEFAULT_CHUNK_OVERLAP = 64

CHUNK_SUFFIX = ".chunks.json"

# llama-index's default sentence tokenizer pulls in nltk (punkt) data that is
# not always loadable (e.g. hardlinked corpora inside a venv). A simple regex
# splitter keeps SentenceSplitter fully offline and self-contained.
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def _regex_sentence_split(text: str) -> list[str]:
    return [chunk for chunk in _SENTENCE_SPLIT_RE.split(text) if chunk]


class Chunk(BaseModel):
    chunk_id: str
    index: int
    text: str
    char_count: int


class ChunkFile(BaseModel):
    source: str
    version: int
    chunk_count: int
    chunks: list[Chunk]


class ChunkerResult(BaseModel):
    chunked: int = 0


def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[str]:
    """Split text into sentence-aligned chunks of up to chunk_size tokens."""
    splitter = SentenceSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        chunking_tokenizer_fn=_regex_sentence_split,
    )
    return [chunk for chunk in splitter.split_text(text) if chunk.strip()]


def _chunk_id(record: FileRecord, index: int) -> str:
    return f"{record.path}:{index}"


class Chunker:
    def __init__(
        self,
        output_dir: str | Path | None = None,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    ):
        self.output_dir = Path(output_dir) if output_dir else None
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_one(self, record: FileRecord) -> FileRecord:
        content = (record.stage_outputs.get("parser") or {}).get("content") or ""
        raw_chunks = chunk_text(content, self.chunk_size, self.chunk_overlap)
        chunk_ids = [_chunk_id(record, i) for i in range(len(raw_chunks))]
        output: dict[str, Any] = {
            "chunk_count": len(raw_chunks),
            "chunk_ids": chunk_ids,
        }

        if self.output_dir is not None and raw_chunks:
            rel = Path(record.path)
            dest = self.output_dir / rel.parent / f"{rel.stem}{CHUNK_SUFFIX}"
            dest.parent.mkdir(parents=True, exist_ok=True)
            payload = ChunkFile(
                source=record.path,
                version=record.version,
                chunk_count=len(raw_chunks),
                chunks=[
                    Chunk(
                        chunk_id=chunk_ids[index],
                        index=index,
                        text=text,
                        char_count=len(text),
                    )
                    for index, text in enumerate(raw_chunks)
                ],
            )
            dest.write_text(payload.model_dump_json(indent=2), encoding="utf-8")
            output["processed_path"] = str(dest)

        record.stage_outputs["chunker"] = output
        return record

    def run(self, records: list[FileRecord]) -> ChunkerResult:
        result = ChunkerResult()
        for record in records:
            self.chunk_one(record)
            if record.stage_outputs["chunker"].get("chunk_count"):
                result.chunked += 1
        return result
