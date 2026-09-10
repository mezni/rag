"""
Thin orchestration stage: runs the Chunker over the files the parser just
produced. All substantive logic lives in src/chunking/chunker.py.
"""

from __future__ import annotations

from src.chunking.chunker import (
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    Chunker,
)
from src.config.logger import get_logger
from src.models.pipeline_context import PipelineContext
from src.pipeline.stage import Stage

logger = get_logger(__name__)


class ChunkerStage(Stage):
    name = "chunker"

    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def run(self, context: PipelineContext) -> PipelineContext:
        run = context.run
        result = Chunker(
            output_dir=run.output_dir or None,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        ).run(context.files_to_process)
        run.files_chunked = result.chunked
        if result.chunked:
            logger.info(f"chunker: chunked {result.chunked} file(s)")
        return context
