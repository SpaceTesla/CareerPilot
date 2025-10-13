from ..app.services.rag.processing.file_processor import FileProcessor

FILE_PATH = "uploads/pdfs/resume-shivansh-ai.pdf"

processor = FileProcessor(FILE_PATH)
docs = processor.documents

print(docs)

with open("processed/resume-shivansh-ai.md", "w") as f:
    joined_content = "\n\n--------------------------------\n\n".join(
        [doc.page_content for doc in docs]
    )
    f.write(joined_content)
