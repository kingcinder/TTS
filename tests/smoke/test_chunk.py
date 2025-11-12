from scripts.tts_chunk import chunk_text

def test_chunk_text_basic():
    text = "Hello world. This is a longer sentence to ensure chunking works properly."
    chunks = chunk_text(text, max_sec=5)
    assert chunks, "Chunking should produce at least one chunk"
    assert all(isinstance(item, str) for item in chunks)
