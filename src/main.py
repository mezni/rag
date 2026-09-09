from config.logger import setup_logger
from config.settings import ApplicationSettings, PipelineSettings, RuntimeSettings
from models.pipeline_context import PipelineContext
from pipeline.pipeline import Pipeline
from pipeline.stages.logging_stage import PipelineLoggingStage

logger = setup_logger("main")


def main() -> None:
    settings = ApplicationSettings(
        pipeline=PipelineSettings(name="Document Processing Pipeline"),
        runtime=RuntimeSettings(
            chunk_size=512,
            chunk_overlap=50,
            max_document_size=1048576,
        ),
    )

    context = PipelineContext(settings=settings)

    pipeline = Pipeline()
    pipeline.add_stage(PipelineLoggingStage())
    pipeline.run(context)


if __name__ == "__main__":
    main()
