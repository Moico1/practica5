from app.chunking import clean_text, split_text


def test_clean_text_collapses_whitespace():
    assert clean_text("  norma\n\n bancaria\t2026 ") == "norma bancaria 2026"


def test_split_text_preserves_overlap():
    chunks = split_text("abcdefghij", chunk_size=6, chunk_overlap=2)
    assert chunks == ["abcdef", "efghij"]


def test_split_text_empty_input():
    assert split_text("   ", 100, 10) == []
