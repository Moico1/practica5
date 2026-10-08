import argparse
import asyncio
import json
import statistics
import time
from datetime import datetime, timezone

from app.config import get_settings
from app.schemas import IngestRequest
from app.services import RAGService


async def measure(service: RAGService, urls: list[str], workers: int, repetition: int, chunk_size: int, chunk_overlap: int, embedding_batch_size: int) -> tuple[float, dict]:
    started = time.perf_counter()
    result = await service.ingest(
        IngestRequest(
            coleccion_id=f"benchmark_{workers}_{repetition}",
            urls=urls,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            concurrency_workers=workers,
            embedding_batch_size=embedding_batch_size,
        )
    )
    return time.perf_counter() - started, result


async def main(urls: list[str], repetitions: int, chunk_size: int, chunk_overlap: int, embedding_batch_size: int) -> None:
    service = RAGService(get_settings())
    measurements = {}
    for workers in (1, 2, 4, 8):
        runs = [
            await measure(service, urls, workers, repetition, chunk_size, chunk_overlap, embedding_batch_size)
            for repetition in range(1, repetitions + 1)
        ]
        measurements[workers] = {
            "durations": [duration for duration, _ in runs],
            "duration": statistics.median(duration for duration, _ in runs),
            "result": runs[0][1],
        }
    baseline = measurements[1]["duration"]
    report = {
        "experiment": {
            "started_at_utc": datetime.now(timezone.utc).isoformat(),
            "urls_count": len(urls),
            "workers": [1, 2, 4, 8],
            "repetitions": repetitions,
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
            "embedding_batch_size": embedding_batch_size,
            "baseline": "workers=1",
            "formulas": {
                "speedup": "T_1 / T_p",
                "efficiency": "speedup / p",
            },
        },
        "measurements": [
            {
                "workers": workers,
                "time_seconds": round(measurements[workers]["duration"], 4),
                "run_times_seconds": [round(value, 4) for value in measurements[workers]["durations"]],
                "speedup": round(baseline / measurements[workers]["duration"], 4) if measurements[workers]["duration"] else None,
                "efficiency": round((baseline / measurements[workers]["duration"]) / workers, 4) if measurements[workers]["duration"] else None,
                "phases": measurements[workers]["result"]["tiempos_por_fase_segundos"],
                "phase_percentages": measurements[workers]["result"]["desglose_porcentual"],
            }
            for workers in measurements
        ],
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mide la ingesta completa con 10 URLs")
    parser.add_argument("urls", nargs="+", help="URLs de prueba de tamaño similar")
    parser.add_argument("--repetitions", type=int, default=1, help="Repeticiones por cantidad de workers (por defecto: 1)")
    parser.add_argument("--chunk-size", type=int, default=1000, help="Tamaño de chunk usado en la prueba")
    parser.add_argument("--chunk-overlap", type=int, default=200, help="Solapamiento entre chunks")
    parser.add_argument("--embedding-batch-size", type=int, default=16, help="Cantidad de chunks por llamada de embeddings")
    args = parser.parse_args()
    if len(args.urls) < 10:
        parser.error("proporciona al menos 10 URLs")
    if args.repetitions < 1:
        parser.error("--repetitions debe ser al menos 1")
    if args.chunk_overlap >= args.chunk_size:
        parser.error("--chunk-overlap debe ser menor que --chunk-size")
    asyncio.run(main(args.urls, args.repetitions, args.chunk_size, args.chunk_overlap, args.embedding_batch_size))
