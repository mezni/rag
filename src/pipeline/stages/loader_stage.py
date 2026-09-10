"""
Thin orchestration stage: scans input_dir via the Loader, runs the
Parser over the files it discovered, and wires the result back into
the pipeline context. All substantive logic lives in
src/ingestion/loader.py and src/ingestion/parser.py.
"""
from __future__ import annotations

from src.config.logger import get_logger
from src.ingestion.loader import Loader
from src.ingestion.parser import Parser
from src.models.pipeline_context import PipelineContext
from src.pipeline.stage import Stage

logger = get_logger(__name__)


class LoaderStage(Stage):
    name = "loader"

    def __init__(self, glob_pattern: str = "**/*"):
        self.glob_pattern = glob_pattern

    def run(self, context: PipelineContext) -> PipelineContext:
        run = context.run
        loader = Loader(run.input_dir, glob_pattern=self.glob_pattern)
        result = loader.run(context.state)

        context.state = result.state
        context.files_to_process = Parser().run(result.files_to_process)

        run.files_scanned = result.scanned
        run.files_new = result.new
        run.files_updated = result.updated
        run.files_unchanged = result.unchanged
        run.files_deleted = result.deleted
        run.files_sent_downstream = len(context.files_to_process)
        return context