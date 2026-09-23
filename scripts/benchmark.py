import argparse
import asyncio
import json
import time

from app.config import get_settings
from app.schemas import IngestRequest
from app.services import RAGService


async def measure(service: RAGService, urls: list[str], workers: int) -> tuple[float, dict]:
    started = time.perf_counter()
    result = await service.ingest(
        IngestRequest(
            coleccion_id=f"benchmark_{workers}",
            urls=urls,
            concurrency_workers=workers,
        )
    )
    return time.perf_counter() - started, result


async def main(urls: list[str]) -> None:
    service = RAGService(get_settings())
    measurements = {}
    for workers in (1, 2, 4, 8):
        duration, result = await measure(service, urls, workers)
        measurements[workers] = {"duration": duration, "result": result}
    baseline = measurements[1]["duration"]
    report = [
        {
            "workers": workers,
            "time_seconds": round(measurements[workers]["duration"], 4),
            "speedup": round(baseline / measurements[workers]["duration"], 4) if measurements[workers]["duration"] else None,
            "efficiency": round((baseline / measurements[workers]["duration"]) / workers, 4) if measurements[workers]["duration"] else None,
            "phases": measurements[workers]["result"]["tiempos_por_fase_segundos"],
        }
        for workers, duration in measurements.items()
    ]
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mide la ingesta completa con 10 URLs")
    parser.add_argument("urls", nargs="+", help="URLs de prueba de tamaño similar")
    args = parser.parse_args()
    if len(args.urls) < 10:
        parser.error("proporciona al menos 10 URLs")
    asyncio.run(main(args.urls))
