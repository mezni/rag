import pytest
from pathlib import Path
from config.settings import ApplicationSettings, PipelineSettings, RuntimeSettings
from config.logger import setup_logger
from ingestion.loader import DirectoryFileLoader, DocumentLoader, Document
from models.pipeline_context import PipelineContext


logger = setup_logger("test_loader")


@pytest.fixture
def sample_settings():
    return ApplicationSettings(
        pipeline=PipelineSettings(name="test"),
        runtime=RuntimeSettings(chunk_size=512, chunk_overlap=50, max_document_size=1048576),
    )


class TestDocumentLoader:
    def test_load_single_document(self, tmp_path):
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        file_path = input_dir / "test.txt"
        file_path.write_text("test content")

        loader = DirectoryFileLoader(input_dir=str(input_dir), output_dir=str(tmp_path / "output"))
        doc = loader.load(str(file_path))

        assert doc.content == "test content"
        assert doc.source == "filesystem"
        assert doc.document_id == "test"  # stem (filename without extension)
        assert doc.format == ".txt"
        assert isinstance(doc.path, Path)
        assert doc.metadata == {"path": str(file_path)}

    def test_scan_and_load_with_existing_dir(self, tmp_path):
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "doc1.txt").write_text("Hello World")
        (input_dir / "subdir").mkdir()
        (input_dir / "subdir" / "doc2.md").write_text("# Markdown")

        loader = DirectoryFileLoader(input_dir=str(input_dir), output_dir=str(tmp_path / "output"))
        docs = loader.scan_and_load()

        assert len(docs) == 2
        assert "doc1.txt" in docs
        assert "subdir/doc2.md" in docs

        # Check first document
        doc1 = docs["doc1.txt"]
        assert doc1.content == "Hello World"
        assert doc1.source == "filesystem"
        assert doc1.format == ".txt"
        assert doc1.metadata == {"path": str(input_dir / "doc1.txt")}

        # Check second document
        doc2 = docs["subdir/doc2.md"]
        assert doc2.content == "# Markdown"
        assert doc2.format == ".md"
        assert doc2.metadata == {"path": str(input_dir / "subdir" / "doc2.md")}

    def test_scan_and_load_nonexistent_dir(self, tmp_path):
        loader = DirectoryFileLoader(input_dir=str(tmp_path / "nonexistent"), output_dir=str(tmp_path / "output"))
        docs = loader.scan_and_load()

        assert docs == {}

    def test_scan_and_load_unsupported_ext(self, tmp_path):
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "doc.xyz").write_text("unsupported")

        loader = DirectoryFileLoader(input_dir=str(input_dir), output_dir=str(tmp_path / "output"))
        docs = loader.scan_and_load()

        assert docs == {}


class TestDocumentLoaderStage:
    def test_execute_loads_docs(self, tmp_path, sample_settings):
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "test.txt").write_text("test content")

        output_dir = tmp_path / "output"

        ctx = PipelineContext(
            settings=sample_settings,
            input_dir=str(input_dir),
            output_dir=str(output_dir),
            documents={},
        )

        from pipeline.stages.loader_stage import DocumentLoaderStage
        stage = DocumentLoaderStage()
        result = stage.execute(ctx)

        assert len(result.documents) == 1
        assert "test.txt" in result.documents
        doc = result.documents["test.txt"]
        assert doc.content == "test content"
        assert doc.source == "filesystem"
        assert doc.format == ".txt"
        assert doc.metadata == {"path": str(input_dir / "test.txt")}

    def test_execute_prepares_output_dirs(self, tmp_path, sample_settings):
        input_dir = tmp_path / "input"
        nested = input_dir / "sub" / "folder"
        nested.mkdir(parents=True, exist_ok=True)
        (nested / "doc.txt").write_text("nested")

        output_dir = tmp_path / "output"

        ctx = PipelineContext(
            settings=sample_settings,
            input_dir=str(input_dir),
            output_dir=str(output_dir),
            documents={},
        )

        from pipeline.stages.loader_stage import DocumentLoaderStage
        stage = DocumentLoaderStage()
        result = stage.execute(ctx)

        assert (output_dir / "sub" / "folder").exists()
        assert len(result.documents) == 1
        doc = result.documents["sub/folder/doc.txt"]
        assert doc.content == "nested"
        assert doc.format == ".txt"
        assert doc.metadata == {"path": str(nested / "doc.txt")}

    def test_execute_with_mixed_extensions(self, tmp_path, sample_settings):
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "doc1.txt").write_text("text")
        (input_dir / "doc2.md").write_text("# markdown")
        (input_dir / "doc3.json").write_text('{"key": "value"}')

        output_dir = tmp_path / "output"

        ctx = PipelineContext(
            settings=sample_settings,
            input_dir=str(input_dir),
            output_dir=str(output_dir),
            documents={},
        )

        from pipeline.stages.loader_stage import DocumentLoaderStage
        stage = DocumentLoaderStage()
        result = stage.execute(ctx)

        assert len(result.documents) == 3
        doc1 = result.documents.get("doc1.txt")
        assert doc1 is not None
        assert doc1.format == ".txt"
        doc2 = result.documents.get("doc2.md")
        assert doc2 is not None
        assert doc2.format == ".md"
        doc3 = result.documents.get("doc3.json")
        assert doc3 is not None
        assert doc3.format == ".json"