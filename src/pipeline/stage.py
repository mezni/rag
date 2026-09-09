from abc import ABC, abstractmethod
from models.pipeline_context import PipelineContext


class Stage(ABC):

    @abstractmethod
    def execute(self, context: PipelineContext) -> PipelineContext:
        pass
