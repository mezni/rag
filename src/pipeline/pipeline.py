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

from pydantic import BaseModel, ConfigDict, field_validator

from src.config.logger import get_logger
from src.models.pipeline_context import PipelineContext, PipelineRun, PipelineState
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

    def run(self, input_dir: str) -> PipelineContext:
        state = self.state_store.load()
        run = PipelineRun(
            run_id=str(uuid.uuid4()),
            started_at=datetime.now(timezone.utc),
            input_dir=input_dir,
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
            run.finished_at = datetime.now(timezone.utc)
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

    def _persist(self, state: PipelineState) -> None:
        if self.max_runs and len(state.runs) > self.max_runs:
            state.runs = state.runs[-self.max_runs:]
        self.state_store.save(state)