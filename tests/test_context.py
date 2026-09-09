import pytest
from pydantic import ValidationError
from config.settings import ApplicationSettings, PipelineSettings, RuntimeSettings
from models.pipeline_context import PipelineContext

def test_pipeline_context_creation():
    settings = ApplicationSettings(
        pipeline=PipelineSettings(name="Test Pipeline"),
        runtime=RuntimeSettings(
            chunk_size=128,
            chunk_overlap=10,
            max_document_size=1024,
        ),
    )
    context = PipelineContext(settings=settings)

    assert context.settings.pipeline.name == "Test Pipeline"
    assert context.settings.runtime.chunk_size == 128

def test_pipeline_context_invalid_settings():
    with pytest.raises(ValidationError):
        PipelineContext(settings=None)

def test_pipeline_context_settings_access():
    settings = ApplicationSettings(
        pipeline=PipelineSettings(name="Another Test"),
        runtime=RuntimeSettings(
            chunk_size=256,
            chunk_overlap=20,
            max_document_size=2048,
        ),
    )
    context = PipelineContext(settings=settings)

    assert context.settings.pipeline.name == "Another Test"
    assert context.settings.runtime.chunk_size == 256
    assert context.settings.runtime.chunk_overlap == 20
    assert context.settings.runtime.max_document_size == 2048
