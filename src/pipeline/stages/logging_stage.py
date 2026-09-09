from config.logger import setup_logger
from models.pipeline_context import PipelineContext
from pipeline.stage import Stage

logger = setup_logger("stage.logging")


class PipelineLoggingStage(Stage):
    """A stage that logs current pipeline context details."""

    def execute(self, context: PipelineContext) -> PipelineContext:
        logger.info(
            f"Configured chunk size: {context.settings.runtime.chunk_size}"
        )
        logger.info(
            f"Configured overlap: {context.settings.runtime.chunk_overlap}"
        )
        return context
