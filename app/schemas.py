from pydantic import BaseModel, Field, HttpUrl, field_validator


class IngestRequest(BaseModel):
    coleccion_id: str = Field(min_length=1, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    urls: list[HttpUrl] = Field(min_length=1)
    chunk_size: int = Field(default=1000, ge=100, le=5000)
    chunk_overlap: int = Field(default=200, ge=0)
    concurrency_workers: int = Field(default=4, ge=1, le=32)
    embedding_batch_size: int = Field(default=16, ge=1, le=100)

    @field_validator("chunk_overlap")
    @classmethod
    def overlap_smaller_than_chunk(cls, value: int, info):
        chunk_size = info.data.get("chunk_size", 1000)
        if value >= chunk_size:
            raise ValueError("chunk_overlap debe ser menor que chunk_size")
        return value


class QueryRequest(BaseModel):
    coleccion_id: str = Field(min_length=1, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    pregunta: str = Field(min_length=1, max_length=2000)
    match_count: int = Field(default=5, ge=1, le=20)


class QueryResponse(BaseModel):
    respuesta: str
    fuentes: list[dict]
