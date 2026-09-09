from pydantic import BaseModel
from config.settings import ApplicationSettings


class PipelineContext(BaseModel):
    """State shared across a single pipeline execution."""

    settings: ApplicationSettings
