import pytest
from pydantic import ValidationError

from app.schemas import IngestRequest


def test_ingest_rejects_overlap_equal_to_chunk_size():
    with pytest.raises(ValidationError):
        IngestRequest(
            coleccion_id="demo",
            urls=["https://example.com"],
            chunk_size=100,
            chunk_overlap=100,
        )


def test_ingest_accepts_expected_request():
    request = IngestRequest(
        coleccion_id="tributaria_2026",
        urls=["https://example.com"],
        chunk_size=1000,
        chunk_overlap=200,
        concurrency_workers=4,
    )
    assert request.concurrency_workers == 4
