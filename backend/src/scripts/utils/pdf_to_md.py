from pathlib import Path

import pymupdf4llm

INPUT = Path("uploads/pdfs/resume-shivansh-ai.pdf")
OUTPUT = Path("processed/resume-shivansh-ai.md")


def main() -> None:
    md = pymupdf4llm.to_markdown(str(INPUT))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(md, encoding="utf-8")
    print(f"Wrote: {OUTPUT}")


if __name__ == "__main__":
    main()
