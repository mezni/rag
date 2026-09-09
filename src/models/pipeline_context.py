from pydantic import BaseModel
from config.settings import ApplicationSettings


class PipelineContext(BaseModel):
    """State shared across a single pipeline execution."""

    settings: ApplicationSettings
    input_dir: str = "data/input"
    output_dir: str = "data/output"
    # Maps relative path (e.g. "subfolder/doc.txt") to file content
    documents: dict[str, str] = {}