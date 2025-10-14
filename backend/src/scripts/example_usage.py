"""
Example usage of ResumeService for API integration.
This shows how to use the service programmatically without argparse.
"""

from app.services.rag.resume_service import ResumeService


def main():
    """Example of using ResumeService programmatically."""

    # Initialize the service
    service = ResumeService()

    # Process a resume file
    resume_data = service.process_resume(
        file_path="processed/resume-shivansh-ai.md",
        enrich=True,  # Use LLM enrichment
        save_output=True,  # Save to file
    )

    # The service returns the JSON data directly
    print("Resume processed successfully!")
    print(f"Name: {resume_data.get('name', 'N/A')}")
    print(f"Email: {resume_data.get('email', 'N/A')}")
    print(f"Experience items: {len(resume_data.get('experience', []))}")
    print(f"Projects: {len(resume_data.get('projects', []))}")

    # You can also process from text directly
    with open("processed/resume-shivansh-ai.md", encoding="utf-8") as f:
        markdown_text = f.read()

    resume_from_text = service.process_resume_from_text(
        markdown_text=markdown_text,
        source_file="resume-shivansh-ai.md",
        enrich=True,
    )

    print("\nProcessed from text successfully!")
    print(f"Name from text: {resume_from_text.get('name', 'N/A')}")


if __name__ == "__main__":
    main()
