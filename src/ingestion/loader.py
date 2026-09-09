from pathlib import Path
from typing import List
from pydantic import BaseModel
import logging

logger = logging.getLogger("ingestion.loader")


class Document(BaseModel):
    """Represents a loaded document with metadata."""

    document_id: str  # e.g., filename without extension or relative pat
    source: str = "filesystem"
    content: str
    path: Path  # Full path to the file
    metadata: dict  # Additional metadata
    status: str = "loaded"  # "loaded" or "format_not_supported"

    @property
    def format(self) -> str:
        """Return the file extension in lowercase (e.g., '.txt', '.md')."""
        return self.path.suffix.lower()

    def __repr__(self) -> str:
        return f"Document(id={self.document_id!r}, format={self.format!r}, status={self.status!r}, source={self.source!r})"


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

        if path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            # Unsupported format - create Document with status "format_not_supported"
            document_id = path.stem  # filename without extension
            metadata = {"path": str(path)}
            return Document(
                content="",
                source="filesystem",
                document_id=document_id,
                path=path,
                metadata=metadata,
                status="format_not_supported",
            )

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
            status="loaded",
        )

    def _get_relative_path(self, file_path: Path, input_dir: Path) -> str:
        """Get relative path from input_dir, with special handling:
        - If file is directly under input_dir, return '.'
        - If file is in a subdirectory, return '/subdir' """
        rel = str(file_path.relative_to(input_dir))
        # If file is directly in input_dir (no directory component)
        if Path(rel).parent == Path('.'):
            return '.'
        # If file is in a subdirectory, return just the directory part
        return '/' + Path(rel).parent.as_posix()

    def scan_and_load(self) -> dict[str, Document]:
        """Recursively scans input_dir and returns mapping of relative path -> Document."""
        documents: dict[str, Document] = {}

        if not self.input_dir.exists():
            logger.warning(f"Input directory does not exist: {self.input_dir}")
            return documents

        # Recursively traverse all items in input_dir
        for file_path in self.input_dir.rglob("*"):
            if file_path.is_file():
                rel_path = str(file_path.relative_to(self.input_dir))

                if file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                    # Supported format - load the document
                    logger.info(f"Discovered and loading file: {rel_path}")
                    doc = self.load(str(file_path))
                    documents[rel_path] = doc
                else:
                    # Unsupported format - create Document with status "format_not_supported"
                    logger.info(f"Unsupported format for file: {rel_path}")
                    document_id = file_path.stem
                    metadata = {"path": str(file_path)}
                    doc = Document(
                        content="",
                        source="filesystem",
                        document_id=document_id,
                        path=file_path,
                        metadata=metadata,
                        status="format_not_supported",
                    )
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

    def __init__(self, input_dir: str = "data/raw", output_dir: str = "data/processed") -> None:
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)

    def load(self, file_path: str) -> Document:
        """Load a single document from the given file path."""
        path = Path(file_path)
        relative_path = str(path.relative_to(self.input_dir))

        if path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            # Unsupported format - create Document with status "format_not_supported"
            document_id = path.stem  # filename without extension
            metadata = {"path": str(path)}

            return Document(
                content="",
                source="filesystem",
                document_id=document_id,
                path=path,
                metadata=metadata,
                status="format_not_supported",
            )

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
            status="loaded",
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
            if file_path.is_file():
                rel_path = str(file_path.relative_to(self.input_dir))

                if file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                    # Supported format - load the document
                    logger.info(f"Discovered and loading file: {rel_path}")
                    doc = self.load(str(file_path))
                    documents[rel_path] = doc
                else:
                    # Unsupported format - create Document with status "format_not_supported"
                    logger.info(f"Unsupported format for file: {rel_path}")
                    document_id = file_path.stem
                    metadata = {"path": str(file_path)}
                    doc = Document(
                        content="",
                        source="filesystem",
                        document_id=document_id,
                        path=file_path,
                        metadata=metadata,
                        status="format_not_supported",
                    )
                    documents[rel_path] = doc

        return documents

    def prepare_output_path(self, relative_path: str) -> Path:
        """Constructs and ensures subdirectories exist in output_dir matching relative_path."""
        target_path = self.output_dir / relative_path
        # Create parents (e.g., data/output/reports/2026/) automatically
        target_path.parent.mkdir(parents=True, exist_ok=True)
        return target_path