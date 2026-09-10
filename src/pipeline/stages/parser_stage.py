"""
Runs the ingestion Parser over whatever files are in flight and
narrows the list to those that parsed cleanly. Files that failed to
parse stay in persisted state (with the error recorded) but are not
passed downstream.
"""
from __future__ import annotations

from src.config.logger import get_logger
from src.ingestion.parser import Parser
from src.models.pipeline_context import PipelineContext
from src.pipeline.stage import Stage

logger = get_logger(__name__)


class ParserStage(Stage):
    name = "parser"

    def run(self, context: PipelineContext) -> PipelineContext:
        run = context.run
        records = Parser(output_dir=run.output_dir or None).run(
            context.files_to_process
        )
        parsed = [
            r
            for r in records
            if (r.stage_outputs["parser"].get("content") or "").strip()
        ]
        dropped = len(records) - len(parsed)
        if dropped:
            logger.warning(
                f"parser: dropped {dropped} file(s) with no usable text"
            )
        context.files_to_process = parsed
        return context