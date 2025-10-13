import argparse
from pathlib import Path

from ..app.services.rag.processing.resume_extractor import (
    GeminiEnricher,
    ResumeExtractor,
)


def slugify(path: Path) -> str:
    base = path.stem.lower()
    base = base.replace(" ", "-")
    return re_sub(r"[^a-z0-9\-]+", "", base)


def re_sub(pattern: str, text: str, repl: str = "") -> str:
    import re

    return re.sub(pattern, repl, text)


def main() -> None:
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
    args = parser.parse_args()

    md_path = Path(args.md)
    if not md_path.exists():
        raise FileNotFoundError(f"Markdown not found: {md_path}")

    extractor = ResumeExtractor()
    resume = extractor.from_markdown(md_path, source_file=str(md_path))
    data = resume.model_dump(mode="json")

    # Enrich by default (uses GOOGLE_API_KEY or settings fallback via config)
    cleaned_text = md_path.read_text(encoding="utf-8")
    enricher = GeminiEnricher()
    data = enricher.enrich(cleaned_text=cleaned_text, resume_json=data)

    import json

    json_str = json.dumps(data, indent=2, ensure_ascii=False)

    out_path = (
        Path(args.out)
        if args.out
        else Path(f"processed/{slugify(md_path)}.resume.v1.json")
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json_str, encoding="utf-8")
    print(f"Wrote: {out_path}")


if __name__ == "__main__":
    main()
