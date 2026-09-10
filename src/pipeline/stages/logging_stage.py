"""
First stage in the pipeline. Pass-through observability: logs the
run's starting conditions (known files and their statuses) and hands
the context to the next stage untouched. Timing per stage is handled
by the Pipeline engine, not here.
"""

from __future__ import annotations

from collections import Counter

from src.config.logger import get_logger
from src.models.pipeline_context import PipelineContext
from src.pipeline.stage import Stage

logger = get_logger(__name__)


class LoggingStage(Stage):
    name = "logging"

    def run(self, context: PipelineContext) -> PipelineContext:
        run = context.run
        runs = context.state.runs
        previous_files = runs[-2].files if len(runs) > 1 else {}
        logger.info(
            f"[logging] run={run.run_id} input_dir={run.input_dir} "
            f"known_files={len(previous_files)}"
        )
        for status, count in Counter(f.status for f in previous_files.values()).items():
            logger.info(f"[logging]   {status.value:9s} {count}")
        return context
