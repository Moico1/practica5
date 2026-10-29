# Evidencias para la entrega

Este documento define las capturas que deben acompañar el informe. No captures secretos: nunca debe aparecer `.env`, `SUPABASE_SERVICE_ROLE_KEY` ni `GEMINI_API_KEY`.

## Convención

Guarda las imágenes en una carpeta local `evidencias/` con estos nombres:

- `01_docker_compose.png`
- `02_health_swagger.png`
- `03_supabase_dimension.png`
- `04_supabase_schema_rpc.png`
- `05_ingesta_resumen.png`
- `06_consulta_coleccion_a.png`
- `07_consulta_coleccion_b.png`
- `08_aislamiento_sin_resultados.png`
- `09_benchmark_resultado.png`
- `10_pruebas_docker.png`

Cada captura debe mostrar la terminal o ventana completa, el comando ejecutado y la respuesta. Recorta únicamente información personal o secretos, no los resultados técnicos.

## Capturas obligatorias

### 01. Contenedorización

Comando:

```bash
docker compose ps
```

Debe verse el servicio `backend` activo y, si aparece, su estado saludable.

### 02. API y Swagger

Ejecuta:

```bash
curl --fail http://localhost:8000/health
```

La respuesta esperada es:

```json
{"status":"ok"}
```

Después abre `http://localhost:8000/docs` y captura los endpoints `/api/ingestar-web` y `/api/consultar`.

### 03. Dimensión vectorial

En Supabase SQL Editor ejecuta:

```sql
select format_type(atttypid, atttypmod) as tipo_embedding
from pg_attribute
where attrelid = 'public.normativa_bancaria'::regclass
  and attname = 'embedding';
```

Debe aparecer `vector(3072)`.

### 04. Aislamiento en SQL

En Supabase SQL Editor muestra la ejecución o el contenido de:

```sql
select indexname, indexdef
from pg_indexes
where tablename = 'normativa_bancaria';
```

Debe verse el índice `normativa_bancaria_coleccion_idx` usando B-Tree. Con embeddings de 3072 dimensiones no se crea un índice HNSW, porque pgvector limita ese índice a 2000 dimensiones para el tipo `vector`; la RPC realiza la búsqueda exacta después del filtro por colección. En otra captura o en la misma pantalla muestra la RPC con:

```sql
where n.coleccion_id = match_collection
order by n.embedding <=> query_embedding
```

La definición debe indicar `language plpgsql stable` y contener `return query`.

### 05. Ingesta y métricas por fase

Ejecuta una ingesta real:

```bash
curl --fail --show-error -X POST http://localhost:8000/api/ingestar-web \
  -H 'Content-Type: application/json' \
  -d '{
    "coleccion_id":"tributaria_2026",
    "urls":["URL_REAL_1","URL_REAL_2"],
    "chunk_size":1000,
    "chunk_overlap":200,
    "concurrency_workers":4,
    "embedding_batch_size":16
  }'
```

La captura debe mostrar `chunks_insertados`, `duracion_segundos`, `tiempos_por_fase_segundos`, `desglose_porcentual` y, si corresponde, `fallos`.

### 06 y 07. Consultas aisladas

Ingresa documentos de dos colecciones distintas y consulta cada una:

```bash
curl --fail --show-error -X POST http://localhost:8000/api/consultar \
  -H 'Content-Type: application/json' \
  -d '{
    "coleccion_id":"tributaria_2026",
    "pregunta":"¿Cuál es la tasa o norma exclusiva del documento tributario?",
    "match_count":5
  }'
```

Repite cambiando `coleccion_id` por `bancaria_2026`. En cada captura deben aparecer únicamente las fuentes de la colección consultada.

### 08. Colección sin antecedentes

```bash
curl --fail --show-error -X POST http://localhost:8000/api/consultar \
  -H 'Content-Type: application/json' \
  -d '{
    "coleccion_id":"coleccion_inexistente",
    "pregunta":"¿Qué información contiene?",
    "match_count":5
  }'
```

Debe aparecer el mensaje:

```text
La colección solicitada no contiene antecedentes relevantes para esta consulta.
```

### 09. Benchmark

Usa al menos 10 URLs públicas de tamaño parecido:

```bash
ENV_FILE=.env docker compose exec backend python scripts/benchmark.py \
  --repetitions 3 \
  URL_1 URL_2 URL_3 URL_4 URL_5 \
  URL_6 URL_7 URL_8 URL_9 URL_10 > benchmark.json
```

Abre `benchmark.json` y captura las mediciones de `workers` 1, 2, 4 y 8, junto con `time_seconds`, `speedup`, `efficiency`, `phases` y `phase_percentages`.

La tabla del informe debe copiar esos valores reales. No escribas tiempos manualmente ni uses resultados inventados.

### 10. Pruebas automatizadas

```bash
ENV_FILE=.env.example docker compose run --rm backend pytest -q
```

La captura debe mostrar la suite completa y el resultado `7 passed` o el número actualizado de pruebas.

## Texto para describir las evidencias

Puedes usar este texto en el informe:

> Las evidencias muestran el despliegue reproducible del backend, la disponibilidad de la API, la dimensión compatible con `gemini-embedding-001`, el índice B-Tree y la RPC de aislamiento por `coleccion_id`. La respuesta de ingesta registra el tiempo total y el desglose de scraping, chunking, embeddings e inserción. Finalmente, las consultas sobre colecciones independientes y la consulta a una colección inexistente demuestran que la recuperación está restringida al namespace solicitado.

## Orden recomendado para la defensa

1. Mostrar `docker compose ps` y `/health`.
2. Abrir Swagger y enseñar los dos endpoints.
3. Mostrar `vector(3072)`, el índice y la RPC en Supabase.
4. Ejecutar o mostrar la ingesta y explicar las cuatro fases.
5. Comparar las consultas de las dos colecciones.
6. Mostrar el caso sin antecedentes.
7. Explicar el benchmark, Speedup, eficiencia, overhead, Amdahl y Gustafson.
8. Cerrar con `pytest` y la reproducibilidad de Docker.
