from pathlib import Path
from typing import List
from pydantic import BaseModel
import logging

logger = logging.getLogger("ingestion.loader")


class Document(BaseModel):
    """Represents a loaded document with metadata."""

    content: str
    source: str = "filesystem"
    document_id: str  # e.g., filename without extension or relative path
    path: Path  # Full path to the file
    metadata: dict  # Additional metadata

    @property
    def format(self) -> str:
        """Return the file extension in lowercase (e.g., '.txt', '.md')."""
        return self.path.suffix.lower()

    def __repr__(self) -> str:
        return f"Document(id={self.document_id!r}, format={self.format!r}, source={self.source!r})"


class DirectoryFileLoader:
    """Handles recursive reading and mirroring directory structures for output."""

    SUPPORTED_EXTENSIONS = {".txt", ".md", ".json", ".yaml", ".yml", ".csv"}

    def __init__(self, input_dir: str, output_dir: str) -> None:
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)

    def load(self, file_path: str) -> Document:
        """Load a single document from the given file path."""
        path = Path(file_path)
        relative_path = str(path.relative_to(self.input_dir))
        content = path.read_text(encoding="utf-8")

        # Generate document_id from the filename (stem) or relative path
        document_id = path.stem  # filename without extension

        metadata = {"path": str(path)}

        return Document(
            content=content,
            source="filesystem",
            document_id=document_id,
            path=path,
            metadata=metadata,
        )

    def scan_and_load(self) -> dict[str, Document]:
        """Recursively scans input_dir and returns mapping of relative path -> Document."""
        documents: dict[str, Document] = {}

        if not self.input_dir.exists():
            logger.warning(f"Input directory does not exist: {self.input_dir}")
            return documents

        # Recursively traverse all items in input_dir
        for file_path in self.input_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                # Retain relative directory path (e.g., "reports/2026/summary.md")
                rel_path = str(file_path.relative_to(self.input_dir))
                logger.info(f"Discovered file: {rel_path}")

                doc = self.load(str(file_path))
                documents[rel_path] = doc

        return documents

    def prepare_output_path(self, relative_path: str) -> Path:
        """Constructs and ensures subdirectories exist in output_dir matching relative_path."""
        target_path = self.output_dir / relative_path
        # Create parents (e.g., data/output/reports/2026/) automatically
        target_path.parent.mkdir(parents=True, exist_ok=True)
        return target_path


class DocumentLoader:
    """Loads documents from the filesystem, tracking relative paths and metadata."""

    SUPPORTED_EXTENSIONS = {".txt", ".md", ".json", ".yaml", ".yml", ".csv"}

    def __init__(self, input_dir: str = "data/input", output_dir: str = "data/output") -> None:
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)

    def load(self, file_path: str) -> Document:
        """Load a single document from the given file path."""
        path = Path(file_path)
        relative_path = str(path.relative_to(self.input_dir))
        content = path.read_text(encoding="utf-8")

        # Generate document_id from the filename (stem) or relative path
        document_id = path.stem  # filename without extension

        metadata = {"path": str(path)}

        return Document(
            content=content,
            source="filesystem",
            document_id=document_id,
            path=path,
            metadata=metadata,
        )

    def load_all(self, paths: List[str]) -> List[Document]:
        """Load multiple documents from a list of file paths."""
        return [self.load(p) for p in paths]

    def scan_and_load(self) -> dict[str, Document]:
        """Recursively scans input_dir and returns mapping of relative path -> Document."""
        documents: dict[str, Document] = {}

        if not self.input_dir.exists():
            logger.warning(f"Input directory does not exist: {self.input_dir}")
            return documents

        # Recursively traverse all items in input_dir
        for file_path in self.input_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                # Retain relative directory path (e.g., "reports/2026/summary.md")
                rel_path = str(file_path.relative_to(self.input_dir))
                logger.info(f"Discovered file: {rel_path}")

                doc = self.load(str(file_path))
                documents[rel_path] = doc

        return documents

    def prepare_output_path(self, relative_path: str) -> Path:
        """Constructs and ensures subdirectories exist in output_dir matching relative_path."""
        target_path = self.output_dir / relative_path
        # Create parents (e.g., data/output/reports/2026/) automatically
        target_path.parent.mkdir(parents=True, exist_ok=True)
        return target_path