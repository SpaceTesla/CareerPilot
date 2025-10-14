import argparse

from ...app.services.resume_processing.resume_service import ResumeService


def main() -> None:
    """CLI script for resume processing."""
    parser = argparse.ArgumentParser(
        description="Convert resume markdown to structured JSON."
    )
    parser.add_argument(
        "--md",
        type=str,
        default="processed/resume-shivansh-ai.md",
        help="Path to markdown produced by pymupdf4llm",
    )
    parser.add_argument("--out", type=str, default=None, help="Output JSON path")
    parser.add_argument("--no-enrich", action="store_true", help="Skip LLM enrichment")
    args = parser.parse_args()

    # Initialize service
    service = ResumeService()

    # Process resume
    data = service.process_resume(
        file_path=args.md,
        enrich=not args.no_enrich,
        save_output=True,
        output_path=args.out,
    )

    print("Resume processing completed successfully!")
    print(f"Processed data keys: {list(data.keys())}")


if __name__ == "__main__":
    main()
