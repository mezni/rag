"""
Pure data contracts. No behavior lives here — persistence is in
src/pipeline/state_store.py, and anything that mutates these belongs
in a Stage.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class FileStatus(str, Enum):
    NEW = "new"
    UPDATED = "updated"
    UNCHANGED = "unchanged"
    DELETED = "deleted"


class FileRecord(BaseModel):
    """Everything the pipeline knows about one scanned file, across all stages."""

    path: str  # relative path, used as the dict key in state
    absolute_path: str
    size_bytes: int
    hash: str
    mtime: float
    first_seen_at: datetime
    last_seen_at: datetime
    last_processed_at: Optional[datetime] = None
    status: FileStatus = FileStatus.NEW

    # Each stage after parsing writes its own key here rather than
    # sharing one blob — keeps provenance traceable.
    # e.g. stage_outputs["parser"] = {"processed_path": "..."}
    #      stage_outputs["chunker"] = {"chunk_count": 42, "chunk_ids": [...]}
    #      stage_outputs["embedder"] = {"embedding_ids": [...]}
    stage_outputs: dict[str, dict[str, Any]] = Field(default_factory=dict)


class PipelineRun(BaseModel):
    """Metadata about a single execution of the pipeline."""

    run_id: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    input_dir: str
    files_scanned: int = 0
    files_new: int = 0
    files_updated: int = 0
    files_unchanged: int = 0
    files_deleted: int = 0
    files_sent_downstream: int = 0
    # per-stage timing/counts, filled in by the Pipeline engine automatically
    stage_timings_seconds: dict[str, float] = Field(default_factory=dict)


class PipelineState(BaseModel):
    """The full persisted state of the pipeline. Loaded/saved each run."""

    version: int = 1
    files: dict[str, FileRecord] = Field(default_factory=dict)
    runs: list[PipelineRun] = Field(default_factory=list)

    def last_run(self) -> Optional[PipelineRun]:
        return self.runs[-1] if self.runs else None


class PipelineContext(BaseModel):
    """
    Threaded through every stage's run(). Stages read from and write to
    this — it's the only thing passed between stages, so its shape is
    the actual contract of your pipeline. Extend it deliberately.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    state: PipelineState
    run: PipelineRun
    # Files the current run needs to act on. Loader populates this with
    # NEW+UPDATED files; later stages narrow or replace it as needed
    # (e.g. parser might drop files it failed to parse).
    files_to_process: list[FileRecord] = Field(default_factory=list)
    # Free-form handoff space for anything that doesn't belong in
    # FileRecord or PipelineRun (e.g. input_dir, cli flags). Keep this
    # small — if a stage needs structured data, prefer stage_outputs.
    scratch: dict[str, Any] = Field(default_factory=dict)
