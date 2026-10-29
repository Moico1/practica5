# Guía final de ejecución

## 1. Credenciales

Abre `.env` en la raíz del proyecto y verifica que tenga estos valores reales:

```env
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_SERVICE_ROLE_KEY=tu_service_role_key
GEMINI_API_KEY=tu_gemini_api_key
EMBEDDING_MODEL=models/gemini-embedding-001
EMBEDDING_DIMENSIONS=3072
GENERATION_MODEL=gemini-3.8-flash
GEMINI_TIMEOUT_SECONDS=20
```

No compartas el archivo `.env` ni subas sus claves a Git.

## 2. Preparar Supabase

### Proyecto nuevo

1. Abre Supabase y entra a **SQL Editor**.
2. Copia todo el contenido de `supabase/schema.sql`.
3. Pulsa **Run**.

Si ya habías ejecutado una versión anterior, vuelve a ejecutar el bloque de la función `match_normativa_coleccion` para actualizarla a `language plpgsql`; después de eso toma la captura de la RPC.

### Proyecto donde se ejecutó una versión anterior

Si anteriormente ejecutaste la versión que usaba `vector(2000)`, ejecuta `supabase/migrate_embedding_dimensions.sql`.

La migración solo funciona si la tabla todavía no tiene filas. Si aparece un error indicando que existen filas, no borres datos: conserva la información y realiza una migración controlada regenerando los embeddings.

Comprueba la dimensión antes de continuar:

```sql
select format_type(atttypid, atttypmod) as tipo_embedding
from pg_attribute
where attrelid = 'public.normativa_bancaria'::regclass
  and attname = 'embedding';
```

El resultado esperado es `vector(3072)`. Si aparece `vector(2000)`, ejecuta nuevamente la migración actualizada y vuelve a comprobarlo.

## 3. Levantar la aplicación

Desde la raíz del proyecto ejecuta:

```bash
docker compose up --build -d
```

Verifica el contenedor:

```bash
docker compose ps
```

Verifica la API:

```bash
curl http://localhost:8000/health
```

Respuesta esperada:

```json
{"status":"ok"}
```

La documentación interactiva queda disponible en:

- http://localhost:8000/docs
- http://localhost:8000/redoc

## 4. Probar ingestión

Esta prueba usa `example.com` y crea una colección llamada `demo_prueba`:

```bash
curl --fail --show-error -X POST http://localhost:8000/api/ingestar-web \
  -H 'Content-Type: application/json' \
  -d '{
    "coleccion_id": "demo_prueba",
    "urls": ["https://example.com"],
    "chunk_size": 500,
    "chunk_overlap": 100,
    "concurrency_workers": 2,
    "embedding_batch_size": 4
  }'
```

La respuesta debe incluir `chunks_insertados`, `duracion_segundos`, `tiempos_por_fase_segundos` y `desglose_porcentual`.

Para la práctica, reemplaza `example.com` por URLs públicas de normativa o manuales del mismo dominio temático.

## 5. Probar consulta RAG

```bash
curl --fail --show-error -X POST http://localhost:8000/api/consultar \
  -H 'Content-Type: application/json' \
  -d '{
    "coleccion_id": "demo_prueba",
    "pregunta": "¿Qué información contiene el documento?",
    "match_count": 5
  }'
```

La respuesta debe contener `respuesta` y `fuentes`.

Para preparar las capturas de la entrega, sigue [docs/EVIDENCIAS.md](docs/EVIDENCIAS.md). Incluye únicamente resultados reales y nunca fotografíes el contenido de `.env`.

## 6. Demostrar aislamiento entre colecciones

1. Ingresa documentos de un dominio con `coleccion_id=tributaria_2026`.
2. Ingresa documentos de otro dominio con `coleccion_id=bancaria_2026`.
3. Consulta cada colección por separado.
4. Comprueba que `fuentes` nunca contiene URLs de la otra colección.
5. Consulta una colección inexistente y verifica el mensaje de ausencia de antecedentes.

La RPC garantiza el aislamiento con:

```sql
where n.coleccion_id = match_collection
```

## 7. Ejecutar benchmark

Prepara al menos 10 URLs públicas de tamaño parecido. Luego ejecuta:

```bash
ENV_FILE=.env docker compose exec backend python scripts/benchmark.py \
  --repetitions 3 \
  URL_1 URL_2 URL_3 URL_4 URL_5 \
  URL_6 URL_7 URL_8 URL_9 URL_10 \
  > benchmark.json
```

El benchmark ejecuta la ingesta completa con `p=1,2,4,8` y genera:

- Tiempo total `T_p`.
- Speedup `S_p = T_1 / T_p`.
- Eficiencia `E_p = S_p / p`.
- Tiempo por fase.
- Repeticiones individuales y mediana por cantidad de workers.
- Metadatos del experimento y porcentajes por fase.

Usa [docs/INFORME_RENDIMIENTO.md](docs/INFORME_RENDIMIENTO.md) para completar el informe de máximo cinco páginas.

## 8. Revisar errores

```bash
docker compose logs --no-color --tail=100 backend
```

Errores frecuentes:

- `expected 3072 dimensions`: ejecuta la migración y confirma que la tabla use `vector(3072)`.
- `Configura SUPABASE...`: revisa `.env` y reinicia Compose.
- `429` o `RESOURCE_EXHAUSTED`: espera y reduce `embedding_batch_size` o `concurrency_workers`.
- `La colección no contiene antecedentes`: primero ingresa documentos con el mismo `coleccion_id`.

## 9. Detener el entorno

```bash
docker compose down
```

Para presentar el proyecto, entrega el código, `.env.example`, `Dockerfile`, `docker-compose.yml`, `supabase/schema.sql`, el informe y el resultado real del benchmark. Nunca entregues `.env`.

## 10. Guion de defensa y evaluación

Muestra al docente esta secuencia:

1. `docker compose ps`: contenedor activo y healthcheck.
2. `curl http://localhost:8000/health`: API disponible.
3. `/docs`: endpoints `/api/ingestar-web` y `/api/consultar`.
4. Ingesta: explica `asyncio + httpx`, `ThreadPoolExecutor`, batching y reintentos.
5. Respuesta de ingesta: muestra tiempos por fase y desglose porcentual.
6. SQL Editor: muestra el índice B-Tree y la línea `where n.coleccion_id = match_collection`.
7. Aislamiento: consulta dos colecciones con documentos diferentes y enseña sus fuentes separadas.
8. `docker compose exec -T backend pytest -q`: resultado esperado, `7 passed`.
9. `benchmark.json`: explica `T_p`, speedup, eficiencia, overhead, Ley de Amdahl y análisis complementario de Gustafson.

| Criterio | Evidencia para obtener el puntaje completo |
|---|---|
| Aislamiento vectorial: 25 | DDL, índice B-Tree, RPC filtrada y demostración con dos colecciones |
| Pipeline concurrente: 25 | Código async, pool de hilos, fallos por URL y respuesta de ingesta |
| Batching/rate limiting: 20 | `embedding_batch_size`, backoff ante 429 y logs/resultado |
| Métricas: 20 | `benchmark.json` real con workers 1, 2, 4 y 8, speedup, eficiencia y fases |
| Docker/reproducibilidad: 10 | `docker compose up --build`, healthcheck y suite `7 passed` |

El proyecto alcanza la evidencia técnica para 100 puntos cuando se adjuntan los resultados reales de la migración, la demostración de aislamiento y el benchmark. No inventes tiempos: usa exactamente la salida generada en tu ejecución.
