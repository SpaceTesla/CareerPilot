"""
Test script for PDF resume processing.
Shows the complete PDF -> JSON workflow.
"""

from app.services.rag.resume_service import ResumeService


def main():
    """Test PDF resume processing."""

    # Initialize the service
    service = ResumeService()

    # Test with PDF file
    print("Processing PDF resume...")
    pdf_data = service.process_resume(
        file_path="uploads/pdfs/resume-shivansh-ai.pdf",
        enrich=True,
        save_output=True,
    )

    print("PDF processing completed!")
    print(f"Name: {pdf_data.get('name', 'N/A')}")
    print(f"Email: {pdf_data.get('email', 'N/A')}")
    print(f"Experience items: {len(pdf_data.get('experience', []))}")
    print(f"Projects: {len(pdf_data.get('projects', []))}")

    # Test with markdown file (existing functionality)
    print("\nProcessing markdown resume...")
    md_data = service.process_resume(
        file_path="processed/resume-shivansh-ai.md",
        enrich=True,
        save_output=False,
    )

    print("Markdown processing completed!")
    print(f"Name: {md_data.get('name', 'N/A')}")
    print(f"Email: {md_data.get('email', 'N/A')}")


if __name__ == "__main__":
    main()
