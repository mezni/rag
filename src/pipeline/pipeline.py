"""
The engine. Knows nothing about loader/parser/chunker specifically —
just loops over whatever Stage list it's given, timing and logging
each one, and persists state at the end.

Per-stage logging/timing lives HERE rather than as a separate
LoggingStage in the stage list — that way every stage gets it for
free, and you can't forget to slot a logging stage in when you add
the 5th one.
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, ConfigDict, field_validator

from src.config.logger import get_logger
from src.models.pipeline_context import (
    FileStatus,
    PipelineContext,
    PipelineRun,
    PipelineState,
)
from src.pipeline.stage import Stage
from src.pipeline.state_store import StateStore

logger = get_logger(__name__)


class Pipeline(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    stages: list[Stage]
    state_store: StateStore
    max_runs: int = 0

    @field_validator("stages")
    @classmethod
    def _stages_must_not_be_empty(cls, stages: list[Stage]) -> list[Stage]:
        if not stages:
            raise ValueError("pipeline needs at least one stage")
        return stages

    @field_validator("stages")
    @classmethod
    def _stage_names_must_be_unique(cls, stages: list[Stage]) -> list[Stage]:
        names = {stage.name for stage in stages}
        if len(names) != len(stages):
            raise ValueError("stage names must be unique")
        return stages

    def run(self, input_dir: str, output_dir: str | None = None) -> PipelineContext:
        first_run = not self.state_store.has_state()
        state = self.state_store.load()
        previous = state.model_copy(deep=True) if not first_run else None
        if previous is not None:
            self.state_store.save_last(previous)

        run = PipelineRun(
            run_id=str(uuid.uuid4()),
            started_at=datetime.now(timezone.utc),
            input_dir=input_dir,
            output_dir=output_dir or "",
        )
        state.runs.append(run)

        context = PipelineContext(state=state, run=run)

        logger.info(f"Run {run.run_id} starting ({len(self.stages)} stages)")

        try:
            for stage in self.stages:
                start = time.monotonic()
                logger.info(
                    f"-> stage '{stage.name}' starting "
                    f"({len(context.files_to_process)} files in flight)"
                )
                context = stage.run(context)
                if not isinstance(context, PipelineContext):
                    raise TypeError(
                        f"Stage '{stage.name}' returned "
                        f"{type(context).__name__}, expected PipelineContext"
                    )
                duration = time.monotonic() - start
                run.stage_timings_seconds[stage.name] = round(duration, 4)
                logger.info(f"<- stage '{stage.name}' finished in {duration:.3f}s")
            if context.state is not state:
                raise RuntimeError(
                    "a stage replaced PipelineContext.state; stages must mutate "
                    "the existing state in place"
                )
            if context.run is not run:
                raise RuntimeError(
                    "a stage replaced PipelineContext.run; stages must mutate "
                    "the existing run in place"
                )
            run.finished_at = datetime.now(timezone.utc)
            self._finalize(context, previous)
            self._persist(state)
        except Exception:
            run.failed = True
            run.finished_at = datetime.now(timezone.utc)
            self._persist(state)
            logger.exception("Pipeline run failed")
            raise

        logger.info(
            f"Run {run.run_id} done: scanned={run.files_scanned} "
            f"new={run.files_new} updated={run.files_updated} "
            f"unchanged={run.files_unchanged} deleted={run.files_deleted}"
        )
        return context

    def _finalize(self, context: PipelineContext, previous: PipelineState | None) -> None:
        if previous is None:
            logger.info("first run: no previous state to diff")
            return
        state = context.state
        output_dir = Path(context.run.output_dir) if context.run.output_dir else None

        new_records = changed_records = unchanged_records = 0
        deleted_records: list[str] = []
        for rel, record in state.files.items():
            if record.status is FileStatus.NEW:
                new_records += 1
            elif record.status is FileStatus.UPDATED:
                changed_records += 1
            elif record.status is FileStatus.UNCHANGED:
                unchanged_records += 1
            else:
                previous_status = previous.files.get(rel)
                if previous_status is not None and (
                    previous_status.status is not FileStatus.DELETED
                ):
                    deleted_records.append(rel)

        for rel in deleted_records:
            if output_dir is None:
                logger.info(f"[diff] deleted: {rel} (mark for removal)")
                continue
            artifact = output_dir / Path(rel).with_suffix(".md")
            if artifact.exists():
                artifact.unlink()
                logger.info(f"[diff] deleted: removed processed artifact {artifact}")
            else:
                logger.info(f"[diff] deleted: {rel} (no processed artifact)")
            for version in artifact.parent.glob(f"{artifact.stem}.v*.md"):
                version.unlink()
                logger.info(f"[diff] deleted: removed version archive {version}")

        logger.info(
            f"[diff] vs previous run: new={new_records} changed={changed_records} "
            f"unchanged={unchanged_records} deleted={len(deleted_records)}"
        )

    def _persist(self, state: PipelineState) -> None:
        if self.max_runs and len(state.runs) > self.max_runs:
            state.runs = state.runs[-self.max_runs:]
        self.state_store.save(state)