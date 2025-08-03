# backend/vector_store.py
import json
import os
import pickle
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

DATA_PATH = "data/parsed_output.json"
FAISS_INDEX_PATH = "data/faiss.index"
METADATA_PATH = "data/metadata.pkl"

model = SentenceTransformer("all-MiniLM-L6-v2")

def build_faiss_index():
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"{DATA_PATH} not found. Run document_processor first.")

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    texts = [item["text"] for item in data]
    embeddings = model.encode(texts, show_progress_bar=True)

    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

    faiss.write_index(index, FAISS_INDEX_PATH)
    with open(METADATA_PATH, "wb") as f:
        pickle.dump(data, f)

    print(f"✅ FAISS index built with {len(data)} chunks")

def search_chunks(query: str, k: int = 3):
    if not os.path.exists(FAISS_INDEX_PATH):
        raise FileNotFoundError("FAISS index not found. Run build_faiss_index first.")

    index = faiss.read_index(FAISS_INDEX_PATH)
    with open(METADATA_PATH, "rb") as f:
        metadata = pickle.load(f)

    query_vec = model.encode([query])
    distances, indices = index.search(np.array(query_vec), k)

    results = []
    for i in indices[0]:
        if i < len(metadata):
            chunk = metadata[i].copy()
            chunk["relevance_score"] = float(1 / (1 + distances[0][0]))  # Normalize relevance
            results.append(chunk)
    return results