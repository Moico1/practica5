from fastapi import FastAPI, HTTPException

from app.config import get_settings
from app.schemas import IngestRequest, QueryRequest, QueryResponse
from app.services import RAGService

app = FastAPI(title="Pipeline RAG Multi-Dominio", version="1.0.0")
service = RAGService(get_settings())


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/ingestar-web")
async def ingest_web(request: IngestRequest):
    try:
        return await service.ingest(request)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/api/consultar", response_model=QueryResponse)
async def query(request: QueryRequest):
    try:
        return await service.query(request)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
