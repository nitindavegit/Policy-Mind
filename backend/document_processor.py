# backend/document_processor.py
import fitz  # PyMuPDF
import re
import os
import json

OUTPUT_PATH = "data/parsed_output.json"

def guess_clause_id(text):
    """Extract clause ID like Code-Excl01 from text."""
    match = re.search(r"\(Code-Excl\d+\)", text)
    return match.group(0) if match else "general"

def save_and_process_pdf(filepath):
    doc = fitz.open(filepath)
    chunks = []
    current_section = ""

    for page in doc:
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if "lines" in block:
                line_text = " ".join([
                    span["text"].strip()
                    for line in block["lines"]
                    for span in line["spans"]
                ]).strip()
                if not line_text:
                    continue

                # Detect new clause by pattern
                if re.match(r"^\d+\)|[A-Z][a-z]+.*\(Code-Excl", line_text):
                    if current_section:
                        chunks.append({
                            "text": current_section.strip(),
                            "clause_id": guess_clause_id(current_section)
                        })
                    current_section = line_text
                else:
                    current_section += " " + line_text

    if current_section:
        chunks.append({
            "text": current_section.strip(),
            "clause_id": guess_clause_id(current_section)
        })

    doc.close()

    # Save chunks
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2)

    print(f"✅ Document parsed into {len(chunks)} chunks and saved to {OUTPUT_PATH}")