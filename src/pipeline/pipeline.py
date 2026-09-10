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
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

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
        state = self.state_store.load()
        previous_files = state.last_run().files if state.runs else {}

        run = PipelineRun(
            run_id=str(uuid.uuid4()),
            started_at=datetime.now(UTC),
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
            run.finished_at = datetime.now(UTC)
            self._finalize(context, previous_files)
            self._persist(state)
        except Exception:
            run.failed = True
            run.finished_at = datetime.now(UTC)
            self._persist(state)
            logger.exception("Pipeline run failed")
            raise

        logger.info(
            f"Run {run.run_id} done: scanned={run.files_scanned} "
            f"new={run.files_new} updated={run.files_updated} "
            f"unchanged={run.files_unchanged} deleted={run.files_deleted}"
        )
        return context

    def _finalize(
        self, context: PipelineContext, previous_files: dict[str, Any]
    ) -> None:
        if not previous_files:
            logger.info("first run: nothing to clean up from a previous run")
            return
        run = context.run
        output_dir = Path(run.output_dir) if run.output_dir else None

        newly_deleted = [
            rel
            for rel, record in run.files.items()
            if record.status is FileStatus.DELETED
            and previous_files.get(rel) is not None
            and previous_files[rel].status is not FileStatus.DELETED
        ]

        for rel in newly_deleted:
            if output_dir is None:
                logger.info(f"[diff] deleted: {rel} (mark for removal)")
                continue
            for suffix in (".txt", ".md", ".chunks.json"):
                artifact = output_dir / Path(rel).with_suffix(suffix)
                if not artifact.exists() and not any(
                    artifact.parent.glob(artifact.stem + ".v*" + suffix)
                ):
                    continue
                if artifact.exists():
                    artifact.unlink()
                    logger.info(f"[diff] deleted: removed {artifact}")
                for version in artifact.parent.glob(artifact.stem + ".v*" + suffix):
                    version.unlink()
                    logger.info(f"[diff] deleted: removed version {version}")

        if newly_deleted:
            logger.info(f"[diff] {len(newly_deleted)} file(s) deleted this run")

    def _persist(self, state: PipelineState) -> None:
        if self.max_runs and len(state.runs) > self.max_runs:
            state.runs = state.runs[-self.max_runs :]
        self.state_store.save(state)
