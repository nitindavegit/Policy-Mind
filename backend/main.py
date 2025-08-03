# backend/main.py
from fastapi import FastAPI, File, UploadFile
import os

app = FastAPI(title="PolicyMind API", version="1.0")

# Import the router from routes.py
from backend.routes import router

# Include the router
app.include_router(router)

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext != ".pdf":
        return {"error": "Only PDF files are supported."}

    file_path = f"data/uploaded_docs/{file.filename}"
    os.makedirs("data/uploaded_docs", exist_ok=True)

    with open(file_path, "wb") as f:
        f.write(await file.read())

    try:
        from backend.document_processor import save_and_process_pdf
        from backend.vector_store import build_faiss_index

        save_and_process_pdf(file_path)
        build_faiss_index()

        return {"status": "success", "message": "Document processed and indexed."}
    except Exception as e:
        return {"status": "error", "message": str(e)}