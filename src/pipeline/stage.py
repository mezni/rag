"""
Every stage takes a PipelineContext and returns a (possibly mutated)
PipelineContext. Nothing else crosses stage boundaries — no extra
constructor args passed in at run-time, no globals. If a stage needs
something, it goes into context.scratch or context.state before that
stage runs.

This constraint is what keeps the Pipeline engine able to just loop
over a list of stages without knowing anything about what each one
does.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from src.models.pipeline_context import PipelineContext


class Stage(ABC):
    name: str = "unnamed_stage"

    @abstractmethod
    def run(self, context: PipelineContext) -> PipelineContext:
        ...