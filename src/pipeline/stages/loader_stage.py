from __future__ import annotations

from src.ingestion.loader import Loader
from src.models.pipeline_context import PipelineContext
from src.pipeline.stage import Stage


class LoaderStage(Stage):
    name = "loader"

    def __init__(self, glob_pattern: str = "**/*"):
        self.glob_pattern = glob_pattern

    def run(self, context: PipelineContext) -> PipelineContext:
        input_dir = context.scratch["input_dir"]
        loader = Loader(input_dir, glob_pattern=self.glob_pattern)
        files_to_process, state = loader.run(context.state)
        context.state = state
        context.files_to_process = files_to_process
        context.run.files_sent_downstream = len(files_to_process)
        return context
