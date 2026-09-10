"""
Thin orchestration stage: runs the Cleaner over the files the parser
just produced. All substantive logic lives in src/ingestion/cleaner.py.
"""

from __future__ import annotations

from src.config.logger import get_logger
from src.ingestion.cleaner import Cleaner
from src.models.pipeline_context import PipelineContext
from src.pipeline.stage import Stage

logger = get_logger(__name__)


class CleanerStage(Stage):
    name = "cleaner"

    def run(self, context: PipelineContext) -> PipelineContext:
        run = context.run
        result = Cleaner().run(context.files_to_process)
        run.files_cleaned = result.cleaned
        if result.cleaned:
            logger.info(f"cleaner: cleaned {result.cleaned} file(s)")
        return context
