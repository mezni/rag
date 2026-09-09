from pathlib import Path
from config.logger import setup_logger
from config.settings import ApplicationSettings, PipelineSettings, RuntimeSettings
from config.config_manager import get_application_settings
from models.pipeline_context import PipelineContext
from pipeline.pipeline import Pipeline
from pipeline.stages.logging_stage import PipelineLoggingStage

logger = setup_logger("main")


def main() -> None:
    CONFIG_PATH = Path("configs/pipeline.yaml")
    settings = get_application_settings(CONFIG_PATH)

    context = PipelineContext(settings=settings)

    pipeline = Pipeline()
    pipeline.add_stage(PipelineLoggingStage())
    pipeline.run(context)


if __name__ == "__main__":
    main()
