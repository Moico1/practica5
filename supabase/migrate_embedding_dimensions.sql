-- Ejecuta este script si ya habías creado la tabla con vector(2000).
-- Es seguro solo cuando todavía no hay filas: los embeddings deben regenerarse
-- con la misma dimensión que usa el modelo configurado.
do $$
declare
  existing_rows bigint;
begin
  select count(*) into existing_rows from public.normativa_bancaria;
  if existing_rows > 0 then
    raise exception 'La tabla contiene % filas. Exporta o elimina los embeddings antes de cambiar la dimensión.', existing_rows;
  end if;

  alter table public.normativa_bancaria
    alter column embedding type vector(3072);
end $$;
