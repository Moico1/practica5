# Pipeline RAG multi-dominio

Implementación de la práctica de Sistemas Paralelos y Distribuidos: scraping concurrente, embeddings por lotes, aislamiento vectorial por `coleccion_id` y consulta RAG con FastAPI.

Para ejecutar el proyecto paso a paso, consulta [GUIA_EJECUCION.md](GUIA_EJECUCION.md).

## Requisitos

- Docker Engine y Docker Compose
- Proyecto Supabase con extensión `pgvector`
- API key de Google Gemini

## Configuración

```bash
cp .env.example .env
```

El archivo que consume Docker es `.env`. La plantilla `.env.example` no contiene credenciales y no debe sustituirlo. Consulta [SETUP_CREDENTIALS.md](SETUP_CREDENTIALS.md) para saber exactamente dónde pegar cada valor.

Completa en `.env`:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY` (solo backend, nunca frontend)
- `GEMINI_API_KEY`

Ejecuta `supabase/schema.sql` desde el SQL Editor de Supabase. La columna usa 3072 dimensiones, que es la dimensión observada en ejecución para `gemini-embedding-001`.

## Ejecución

```bash
docker compose up --build
```

La API queda en `http://localhost:8000` y su documentación en `/docs`.

## Ejemplos

```bash
curl -X POST http://localhost:8000/api/ingestar-web \
  -H 'Content-Type: application/json' \
  -d '{"coleccion_id":"tributaria_bolivia_2026","urls":["https://www.impuestos.gob.bo/"],"chunk_size":1000,"chunk_overlap":200,"concurrency_workers":4}'
```

```bash
curl -X POST http://localhost:8000/api/consultar \
  -H 'Content-Type: application/json' \
  -d '{"coleccion_id":"tributaria_bolivia_2026","pregunta":"¿Cuál es la norma aplicable?"}'
```

## Pruebas locales

```bash
python3 -m pip install -r requirements.txt
python3 -m pytest -q
```

## Benchmark para el informe

Con 10 URLs públicas de tamaño parecido, ejecuta la ingesta completa para `p = 1, 2, 4, 8`:

```bash
ENV_FILE=.env docker compose exec backend python scripts/benchmark.py URL_1 URL_2 URL_3 URL_4 URL_5 URL_6 URL_7 URL_8 URL_9 URL_10 > benchmark.json
```

El resultado incluye `T_p`, speedup, eficiencia y el porcentaje de tiempo en cada etapa. La plantilla [docs/INFORME_RENDIMIENTO.md](docs/INFORME_RENDIMIENTO.md) contiene el diagrama, las fórmulas, el protocolo y la prueba de cero contaminación cruzada.

La RPC filtra por `coleccion_id` antes de ordenar por distancia coseno, por lo que una consulta nunca puede recuperar filas de otra colección.
