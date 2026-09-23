# Contexto para continuar el proyecto

## Objetivo

Este repositorio implementa una práctica de Sistemas Paralelos y Distribuidos: un pipeline RAG multi-dominio con scraping concurrente, embeddings Gemini, Supabase/pgvector, aislamiento por `coleccion_id`, métricas de speedup y contenedorización.

## Estado actual

- FastAPI implementado en `app/main.py`.
- Scraping concurrente con `asyncio` + `httpx` en `app/services.py`.
- Limpieza HTML con BeautifulSoup.
- Chunking con solapamiento y paralelización mediante `ThreadPoolExecutor`.
- Embeddings por lotes usando `models/gemini-embedding-001`.
- Dimensión confirmada en ejecución: `3072`.
- Reintentos exponenciales para 429, RESOURCE_EXHAUSTED y timeout.
- Inserción en Supabase por lotes.
- Consulta RAG filtrada obligatoriamente por `coleccion_id`.
- Generación con temperatura 0.0 y respuesta explícita cuando no existen antecedentes.
- SQL con índice B-Tree, HNSW y RPC `match_normativa_coleccion`.
- Docker Compose funcional.
- Suite dentro del contenedor: `7 passed`.
- Healthcheck verificado: `{"status":"ok"}`.

## Archivos importantes

- `app/services.py`: scraping, chunking, embeddings, inserción, consulta y métricas.
- `app/schemas.py`: validación de payloads.
- `supabase/schema.sql`: tabla, índices y RPC.
- `supabase/migrate_embedding_dimensions.sql`: migra una tabla vacía de vector(2000) a vector(3072).
- `GUIA_EJECUCION.md`: pasos completos y guion de defensa.
- `docs/INFORME_RENDIMIENTO.md`: plantilla del informe.
- `scripts/benchmark.py`: benchmark completo para workers 1, 2, 4 y 8.
- `tests/`: pruebas unitarias y contrato SQL.

## Variables secretas

El archivo `.env` existe localmente y está ignorado por Git. Nunca leer, imprimir, copiar o subir su contenido. La plantilla pública es `.env.example`.

Variables requeridas:

```env
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...
GEMINI_API_KEY=...
EMBEDDING_MODEL=models/gemini-embedding-001
EMBEDDING_DIMENSIONS=3072
GENERATION_MODEL=gemini-2.5-flash
```

## Comandos principales

```bash
ENV_FILE=.env docker compose up --build -d
curl http://localhost:8000/health
ENV_FILE=.env docker compose exec -T backend pytest -q
```

Swagger: `http://localhost:8000/docs`.

## Pendiente crítico

La última prueba de ingesta mostró que la tabla remota seguía en `vector(2000)` aunque el código ya usa `3072`. En Supabase SQL Editor hay que ejecutar la versión actual de `supabase/migrate_embedding_dimensions.sql` y comprobar:

```sql
select format_type(atttypid, atttypmod)
from pg_attribute
where attrelid = 'public.normativa_bancaria'::regclass
and attname = 'embedding';
```

Debe devolver `vector(3072)`. Después probar:

```bash
curl --fail --show-error -X POST http://localhost:8000/api/ingestar-web \
  -H 'Content-Type: application/json' \
  -d '{"coleccion_id":"demo_prueba","urls":["https://example.com"],"chunk_size":500,"chunk_overlap":100,"concurrency_workers":2,"embedding_batch_size":4}'
```

Luego probar `/api/consultar`, dos colecciones distintas para demostrar cero contaminación cruzada y el benchmark con 10 URLs reales.

## Evaluación

La implementación está preparada para la rúbrica completa, pero no se deben inventar resultados de benchmark. Para cerrar la evidencia de 100 puntos hacen falta:

1. Confirmar `vector(3072)` en Supabase.
2. Obtener respuesta exitosa de ingesta real.
3. Demostrar aislamiento entre dos colecciones.
4. Generar `benchmark.json` con workers 1, 2, 4 y 8.
5. Completar el informe con los tiempos reales.

## Reglas para la siguiente IA

- No tocar ni exponer `.env`.
- Mantener `EMBEDDING_DIMENSIONS=3072` salvo que se cambie el modelo y se migre la base.
- Validar después de cada cambio con `compileall`, `pytest` dentro del contenedor y `docker compose config`.
- No afirmar que la ingesta funciona hasta ejecutar una prueba real exitosa.
- No inventar métricas.
- Mantener el aislamiento obligatorio por `coleccion_id` en toda consulta.
