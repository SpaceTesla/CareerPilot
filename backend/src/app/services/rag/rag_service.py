"""
Main RAG service that orchestrates all resume processing, retrieval, and storage.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .processing.resume_processor import ResumeProcessor
from .retrieval.resume_retriever import ResumeRetriever
from .vectorstore.resume_vectorstore import ResumeVectorStore


class RAGService:
    """
    Main RAG service that orchestrates resume processing, storage, and retrieval.
    """

    def __init__(
        self,
        processor: ResumeProcessor | None = None,
        vectorstore: ResumeVectorStore | None = None,
        retriever: ResumeRetriever | None = None,
    ) -> None:
        self.processor = processor or ResumeProcessor()
        self.vectorstore = vectorstore or ResumeVectorStore()
        self.retriever = retriever or ResumeRetriever()

    def process_and_store_resume(
        self,
        file_path: str | Path,
        enrich: bool = True,
        save_markdown: bool = False,
    ) -> str:
        """
        Process a resume and store it in the vector store.

        Args:
            file_path: Path to the resume file (PDF or markdown)
            enrich: Whether to enrich the data using LLM
            save_markdown: Whether to save intermediate markdown (for PDF inputs)

        Returns:
            ID of the stored resume
        """
        # Process the resume
        resume_data = self.processor.process(
            file_path=file_path,
            enrich=enrich,
            save_markdown=save_markdown,
        )

        # Store in vector store
        resume_id = self.vectorstore.add_resume(resume_data)
        return resume_id

    def search_resumes(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """
        Search for resumes matching the query.

        Args:
            query: Search query string
            limit: Maximum number of results to return

        Returns:
            List of matching resume data
        """
        return self.retriever.search(query, limit)

    def get_resume(self, resume_id: str) -> dict[str, Any] | None:
        """
        Get a resume by ID.

        Args:
            resume_id: ID of the resume

        Returns:
            Resume data or None if not found
        """
        return self.vectorstore.get_resume(resume_id)

    def find_similar_resumes(
        self, resume_id: str, limit: int = 5
    ) -> list[dict[str, Any]]:
        """
        Find resumes similar to the given resume.

        Args:
            resume_id: ID of the reference resume
            limit: Maximum number of similar resumes to return

        Returns:
            List of similar resume data
        """
        return self.retriever.find_similar(resume_id, limit)
