# scripts/build_index.py
import os
from backend.document_processor import save_and_process_pdf
from backend.vector_store import build_faiss_index

DOCS_DIR = "data/uploaded_docs"

def build_from_all_pdfs():
    pdf_files = [f for f in os.listdir(DOCS_DIR) if f.lower().endswith(".pdf")]
    if not pdf_files:
        print("❌ No PDFs found in", DOCS_DIR)
        return

    for filename in pdf_files:
        path = os.path.join(DOCS_DIR, filename)
        print(f"📄 Processing {filename}...")
        save_and_process_pdf(path)

    print("✅ All PDFs processed. Building FAISS index...")
    build_faiss_index()
    print("🎉 Index built successfully!")

if __name__ == "__main__":
    build_from_all_pdfs()