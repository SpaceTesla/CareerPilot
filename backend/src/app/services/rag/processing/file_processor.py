from pathlib import Path

from docling.chunking import HybridChunker
from langchain_core.documents import Document
from langchain_docling import DoclingLoader
from transformers import AutoTokenizer


class FileProcessor:
    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)
        self._processed_docs: list[Document] | None = None

    def _validate_file(self) -> None:
        """Validate that the file exists and is readable."""
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {self.file_path}")

        if not self.file_path.is_file():
            raise ValueError(f"Path is not a file: {self.file_path}")

        # Support more file types that Docling can handle
        supported_extensions = {".pdf", ".docx", ".pptx", ".xlsx", ".html", ".md"}
        if self.file_path.suffix.lower() not in supported_extensions:
            raise ValueError(
                f"Unsupported file type: {self.file_path.suffix}. \
                    Supported: {supported_extensions}"
            )

    def process(self) -> list[Document]:
        """Process the file and return document chunks."""
        if self._processed_docs is not None:
            return self._processed_docs

        self._validate_file()

        EMBEDDING_MODEL = "BAAI/bge-large-en-v1.5"
        MAX_TOKENS = 256
        tokenizer = AutoTokenizer.from_pretrained(EMBEDDING_MODEL)

        try:
            loader = DoclingLoader(
                file_path=str(self.file_path),
                chunker=HybridChunker(
                    tokenizer=tokenizer,
                    max_tokens=MAX_TOKENS,
                ),
            )
            self._processed_docs = loader.load()
            return self._processed_docs

        except Exception as e:
            raise RuntimeError(
                f"Failed to process file {self.file_path}: {str(e)}"
            ) from e

    @property
    def documents(self) -> list[Document]:
        """Get processed documents (lazy loading)."""
        return self.process()
