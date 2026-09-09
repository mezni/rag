from config.logger import setup_logger
from ingestion.loader import DirectoryFileLoader
from models.pipeline_context import PipelineContext
from pipeline.stage import Stage

logger = setup_logger("stage.loader")


class DocumentLoaderStage(Stage):
    """Pipeline stage that checks nested directory files and creates matching output dirs."""

    def execute(self, context: PipelineContext) -> PipelineContext:
        loader = DirectoryFileLoader(
            input_dir=context.input_dir,
            output_dir=context.output_dir,
        )

        loaded_docs = loader.scan_and_load()
        context.documents.update(loaded_docs)

        # Pre-create corresponding output subdirectories without writing data
        for rel_path in loaded_docs.keys():
            target_path = loader.prepare_output_path(rel_path)
            logger.info(f"Prepared nested output target: {target_path}")

        logger.info(
            f"Successfully checked {len(loaded_docs)} nested document(s)."
        )
        return context