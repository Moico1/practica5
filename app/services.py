import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup
from google import genai
from postgrest.exceptions import APIError
from supabase import Client, create_client

from app.chunking import split_text
from app.config import Settings
from app.schemas import IngestRequest, QueryRequest


@dataclass
class DownloadedPage:
    url: str
    text: str
    error: str | None = None


class RAGService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.supabase: Client | None = None
        self.genai_client = None
        if settings.supabase_url and settings.supabase_service_role_key:
            self.supabase = create_client(settings.supabase_url, settings.supabase_service_role_key)
        if settings.gemini_api_key:
            self.genai_client = genai.Client(api_key=settings.gemini_api_key)

    def _require_integrations(self) -> None:
        if not self.supabase or not self.genai_client:
            raise RuntimeError("Configura SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY y GEMINI_API_KEY")

    async def _download(self, client: httpx.AsyncClient, url: str) -> DownloadedPage:
        try:
            response = await client.get(url)
            response.raise_for_status()
            if len(response.content) > self.settings.max_content_bytes:
                return DownloadedPage(url, "", "respuesta demasiado grande")
            soup = BeautifulSoup(response.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            return DownloadedPage(url, " ".join(soup.stripped_strings))
        except (httpx.HTTPError, UnicodeError) as exc:
            return DownloadedPage(url, "", str(exc))

    async def download_pages(self, urls: list[str], workers: int) -> list[DownloadedPage]:
        limits = httpx.Limits(max_connections=workers, max_keepalive_connections=workers)
        timeout = httpx.Timeout(self.settings.http_timeout_seconds)
        semaphore = asyncio.Semaphore(workers)
        headers = {"User-Agent": "RAG-Lab-Scraper/1.0 (+educational-project)"}
        unique_urls = list(dict.fromkeys(urls))
        async with httpx.AsyncClient(timeout=timeout, limits=limits, follow_redirects=True, headers=headers) as client:
            async def bounded(url: str) -> DownloadedPage:
                async with semaphore:
                    return await self._download(client, url)
            return await asyncio.gather(*(bounded(url) for url in unique_urls))

    async def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        self._require_integrations()
        for attempt in range(self.settings.max_retries):
            try:
                result = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.genai_client.models.embed_content,
                        model=self.settings.embedding_model,
                        contents=texts,
                    ),
                    timeout=self.settings.gemini_timeout_seconds,
                )
                embeddings = [embedding.values for embedding in result.embeddings]
                if any(len(values) != self.settings.embedding_dimensions for values in embeddings):
                    actual = sorted({len(values) for values in embeddings})
                    raise RuntimeError(
                        f"Dimensión inesperada en embeddings: {actual}; "
                        f"se esperaba {self.settings.embedding_dimensions}"
                    )
                return embeddings
            except Exception as exc:
                message = str(exc).upper()
                retryable = any(token in message for token in ("429", "RESOURCE_EXHAUSTED", "RATE LIMIT", "TIMEOUT"))
                if not retryable:
                    raise RuntimeError(f"Error no recuperable generando embeddings: {exc}") from exc
                if attempt == self.settings.max_retries - 1:
                    raise RuntimeError(f"Error generando embeddings: {exc}") from exc
                await asyncio.sleep(2**attempt)
        return []

    async def _generate_answer(self, prompt: str) -> str:
        self._require_integrations()
        for attempt in range(self.settings.max_retries):
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.genai_client.models.generate_content,
                        model=self.settings.generation_model,
                        contents=prompt,
                        config={"temperature": 0.0},
                    ),
                    timeout=self.settings.gemini_timeout_seconds,
                )
                return response.text
            except Exception as exc:
                message = str(exc).upper()
                retryable = any(token in message for token in ("429", "503", "UNAVAILABLE", "RESOURCE_EXHAUSTED", "TIMEOUT"))
                if not retryable:
                    raise RuntimeError(f"Error no recuperable generando la respuesta: {exc}") from exc
                if attempt == self.settings.max_retries - 1:
                    raise RuntimeError(f"Error temporal de Gemini generando la respuesta: {exc}") from exc
                await asyncio.sleep(2**attempt)
        raise RuntimeError("No se pudo generar la respuesta")

    async def ingest(self, request: IngestRequest) -> dict:
        self._require_integrations()
        started = time.perf_counter()
        phase_times = {"scraping_red": 0.0, "chunking_cpu": 0.0, "api_embeddings": 0.0, "insercion_supabase": 0.0}
        scrape_started = time.perf_counter()
        pages = await self.download_pages([str(url) for url in request.urls], request.concurrency_workers)
        phase_times["scraping_red"] = time.perf_counter() - scrape_started
        chunk_started = time.perf_counter()
        chunks: list[dict] = []
        failures = []
        valid_pages = [page for page in pages if not page.error]
        failures = [{"url": page.url, "error": page.error} for page in pages if page.error]
        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor(max_workers=request.concurrency_workers) as pool:
            chunk_futures = [
                loop.run_in_executor(pool, split_text, page.text, request.chunk_size, request.chunk_overlap)
                for page in valid_pages
            ]
            page_chunks = await asyncio.gather(*chunk_futures)
        for page, contents in zip(valid_pages, page_chunks, strict=True):
            for index, content in enumerate(contents):
                chunks.append({"coleccion_id": request.coleccion_id, "contenido": content, "fuente_url": page.url, "chunk_index": index})
        phase_times["chunking_cpu"] = time.perf_counter() - chunk_started

        inserted = 0
        for offset in range(0, len(chunks), request.embedding_batch_size):
            batch = chunks[offset : offset + request.embedding_batch_size]
            embedding_started = time.perf_counter()
            embeddings = await self._embed_batch([item["contenido"] for item in batch])
            phase_times["api_embeddings"] += time.perf_counter() - embedding_started
            rows = [{**item, "embedding": embedding} for item, embedding in zip(batch, embeddings, strict=True)]
            insertion_started = time.perf_counter()
            try:
                self.supabase.table("normativa_bancaria").insert(rows).execute()
            except APIError as exc:
                message = str(exc)
                if "dimension" in message.lower():
                    raise RuntimeError(
                        "Supabase rechazó el embedding por un problema de dimensión. "
                        f"Detalle devuelto por Supabase: {message}"
                    ) from exc
                raise RuntimeError(f"Error insertando en Supabase: {message}") from exc
            phase_times["insercion_supabase"] += time.perf_counter() - insertion_started
            inserted += len(rows)
        total = time.perf_counter() - started
        percentages = {name: round((duration / total) * 100, 2) if total else 0 for name, duration in phase_times.items()}
        return {
            "coleccion_id": request.coleccion_id,
            "urls_solicitadas": len(request.urls),
            "urls_procesadas": len(pages) - len(failures),
            "chunks_insertados": inserted,
            "fallos": failures,
            "duracion_segundos": round(total, 3),
            "tiempos_por_fase_segundos": {name: round(duration, 3) for name, duration in phase_times.items()},
            "desglose_porcentual": percentages,
        }

    async def query(self, request: QueryRequest) -> dict:
        self._require_integrations()
        embeddings = await self._embed_batch([request.pregunta])
        try:
            result = self.supabase.rpc("match_normativa_coleccion", {"query_embedding": embeddings[0], "match_collection": request.coleccion_id, "match_count": request.match_count}).execute()
        except APIError as exc:
            raise RuntimeError(f"Error consultando la RPC de Supabase: {exc}") from exc
        sources = result.data or []
        if not sources:
            return {"respuesta": "La colección solicitada no contiene antecedentes relevantes para esta consulta.", "fuentes": []}
        context = "\n\n".join(f"Fuente: {item['fuente_url']}\n{item['contenido']}" for item in sources)
        prompt = f"Responde únicamente con el contexto de la colección {request.coleccion_id}. Si no hay respuesta explícita, declara que no hay antecedentes. No inventes datos.\n\nContexto:\n{context}\n\nPregunta: {request.pregunta}"
        answer = await self._generate_answer(prompt)
        return {"respuesta": answer, "fuentes": sources}
