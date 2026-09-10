"""
Thin orchestration stage: scans input_dir via the Loader and wires
the result back into the pipeline context's current run. All
substantive logic lives in src/ingestion/loader.py.
"""
from __future__ import annotations

from src.config.logger import get_logger
from src.ingestion.loader import Loader
from src.models.pipeline_context import PipelineContext
from src.pipeline.stage import Stage

logger = get_logger(__name__)


class LoaderStage(Stage):
    name = "loader"

    def __init__(self, glob_pattern: str = "**/*"):
        self.glob_pattern = glob_pattern

    def run(self, context: PipelineContext) -> PipelineContext:
        run = context.run
        runs = context.state.runs
        previous_files = runs[-2].files if len(runs) > 1 else {}
        loader = Loader(
            input_dir=run.input_dir,
            glob_pattern=self.glob_pattern,
            output_dir=run.output_dir or None,
        )
        result = loader.run(previous_files)

        context.files_to_process = result.files_to_process
        run.files = result.files
        run.files_scanned = result.scanned
        run.files_new = result.new
        run.files_updated = result.updated
        run.files_unchanged = result.unchanged
        run.files_deleted = result.deleted
        run.files_sent_downstream = len(context.files_to_process)
        return context