"""
Test script for the new RAG architecture.
Shows how to use the different service layers.
"""

from app.services.rag.rag_service import RAGService
from app.services.resume_processing.processors.processor import ResumeProcessor
from app.services.resume_processing.resume_service import ResumeService


def main():
    """Test the new architecture layers."""

    print("=== Testing New RAG Architecture ===\n")

    # 1. Test ResumeProcessor (lowest level)
    print("1. Testing ResumeProcessor (processing layer):")
    processor = ResumeProcessor()
    data = processor.process(
        file_path="uploads/pdfs/resume-shivansh-ai.pdf",
        enrich=True,
        save_markdown=True,
    )
    print(f"   ✓ Processed resume: {data.get('name', 'N/A')}")

    # 2. Test ResumeService (orchestration layer)
    print("\n2. Testing ResumeService (orchestration layer):")
    service = ResumeService()
    data = service.process_resume(
        file_path="uploads/pdfs/resume-shivansh-ai.pdf",
        enrich=True,
        save_output=True,
        save_markdown=True,
    )
    print(f"   ✓ Processed and saved resume: {data.get('name', 'N/A')}")

    # 3. Test RAGService (full RAG layer)
    print("\n3. Testing RAGService (full RAG layer):")
    rag_service = RAGService()
    resume_id = rag_service.process_and_store_resume(
        file_path="uploads/pdfs/resume-shivansh-ai.pdf",
        enrich=True,
        save_markdown=True,
    )
    print(f"   ✓ Processed and stored resume with ID: {resume_id}")

    # 4. Test retrieval (placeholder)
    print("\n4. Testing retrieval (placeholder):")
    similar_resumes = rag_service.find_similar_resumes(resume_id, limit=3)
    print(f"   ✓ Found {len(similar_resumes)} similar resumes")

    print("\n=== Architecture Test Complete ===")
    print("\nArchitecture layers:")
    print("├── RAGService (orchestrates everything)")
    print("│   ├── ResumeProcessor (handles PDF → JSON)")
    print("│   ├── ResumeVectorStore (stores embeddings)")
    print("│   └── ResumeRetriever (searches resumes)")
    print("└── ResumeService (API-friendly wrapper)")


if __name__ == "__main__":
    main()
