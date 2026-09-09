from pydantic import BaseModel


class PipelineSettings(BaseModel):
    name: str


class RuntimeSettings(BaseModel):
    chunk_size: int
    chunk_overlap: int
    max_document_size: int


class ApplicationSettings(BaseModel):
    pipeline: PipelineSettings
    runtime: RuntimeSettings
