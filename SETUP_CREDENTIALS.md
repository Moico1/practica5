# Configuración de credenciales

El archivo que usa Docker es `.env`, no `.env.example`.

1. Abre `.env` en la raíz del proyecto.
2. Pega los valores después del signo `=`:

```env
SUPABASE_URL=https://TU-PROYECTO.supabase.co
SUPABASE_SERVICE_ROLE_KEY=TU_SERVICE_ROLE_KEY
GEMINI_API_KEY=TU_GEMINI_API_KEY
```

3. Guarda el archivo y ejecuta:

```bash
docker compose up --build
```

`SUPABASE_SERVICE_ROLE_KEY` y `GEMINI_API_KEY` son secretos. No los pegues en el README, no los subas a Git y no los compartas en capturas. `.env` está excluido por `.gitignore`; `.env.example` solo documenta los nombres de las variables.

Antes de iniciar la API, ejecuta `supabase/schema.sql` en el SQL Editor de Supabase. Si ejecutaste la migración anterior que dejó la columna en 2000 dimensiones, ejecuta ahora `supabase/migrate_embedding_dimensions.sql`; como la prueba no insertó datos válidos, puede cambiarla de nuevo a 3072 dimensiones.
