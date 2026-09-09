from config.logger import setup_logger
from models.pipeline_context import PipelineContext
from pipeline.stage import Stage

logger = setup_logger("pipeline")


class Pipeline:

    def __init__(self) -> None:
        self._stages: list[Stage] = []

    def add_stage(self, stage: Stage) -> None:
        self._stages.append(stage)
        logger.info(f"Registered stage: {stage.__class__.__name__}")

    def run(self, context: PipelineContext) -> PipelineContext:
        logger.info(f"Starting pipeline '{context.settings.pipeline.name}'")

        for stage in self._stages:
            stage_name = stage.__class__.__name__
            logger.info(f"Executing stage: {stage_name}")
            context = stage.execute(context)

        logger.info("Pipeline execution completed successfully.")
        return context
