# backend/routes.py
from fastapi import APIRouter
from pydantic import BaseModel
from backend.pipeline import run_pipeline

router = APIRouter()

class QueryRequest(BaseModel):
    query: str

@router.post("/query")
async def query_handler(payload: QueryRequest):
    result = run_pipeline(payload.query)
    return result