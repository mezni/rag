import pytest
from config.logger import setup_logger
from config.settings import ApplicationSettings, PipelineSettings, RuntimeSettings
from models.pipeline_context import PipelineContext
from pipeline.pipeline import Pipeline
from pipeline.stages.logging_stage import PipelineLoggingStage
from config.config_manager import get_application_settings
from pathlib import Path

logger = setup_logger("test_pipeline")

def test_pipeline_initialization():
    logger.info("Starting test_pipeline_initialization")
    pipeline = Pipeline()
    assert len(pipeline._stages) == 0

def test_pipeline_add_stage():
    logger.info("Starting test_pipeline_add_stage")
    pipeline = Pipeline()
    initial_count = len(pipeline._stages)

    class DummyStage:
        pass

    pipeline.add_stage(DummyStage())
    assert len(pipeline._stages) == initial_count + 1

def test_pipeline_run():
    logger.info("Starting test_pipeline_run")
    pipeline = Pipeline()

    settings = ApplicationSettings(
        pipeline=PipelineSettings(name="Test Pipeline"),
        runtime=RuntimeSettings(
            chunk_size=512,
            chunk_overlap=50,
            max_document_size=1048576,
        ),
    )
    context = PipelineContext(settings=settings)

    # Add a simple stub stage
    class DummyStage:
        def execute(self, ctx):
            return ctx

    pipeline.add_stage(DummyStage())
    result = pipeline.run(context)
    assert result is context

def test_pipeline_with_logging_stage():
    logger.info("Starting test_pipeline_with_logging_stage")
    pipeline = Pipeline()
    pipeline.add_stage(PipelineLoggingStage())

    settings = ApplicationSettings(
        pipeline=PipelineSettings(name="Logging Test"),
        runtime=RuntimeSettings(
            chunk_size=256,
            chunk_overlap=25,
            max_document_size=524288,
        ),
    )
    context = PipelineContext(settings=settings)
    result = pipeline.run(context)
    assert result is context

def test_pipeline_load_settings_from_yaml():
    logger.info("Starting test_pipeline_load_settings_from_yaml")
    yaml_path = Path("configs/pipeline.yaml")
    settings = get_application_settings(yaml_path)

    assert settings is not None
    assert settings.pipeline.name == "Document Processing Pipeline"
    assert settings.runtime.chunk_size == 512
    assert settings.runtime.chunk_overlap == 50
    assert settings.runtime.max_document_size == 1048576