from pathlib import Path


SCHEMA = Path(__file__).parents[1] / "supabase" / "schema.sql"


def test_rpc_filters_by_collection_before_similarity_ordering():
    sql = SCHEMA.read_text()
    assert "where n.coleccion_id = match_collection" in sql.lower()
    assert "order by n.embedding <=> query_embedding" in sql.lower()


def test_collection_has_btree_index():
    sql = SCHEMA.read_text()
    assert "normativa_bancaria_coleccion_idx" in sql
    assert "using btree (coleccion_id)" in sql.lower()
