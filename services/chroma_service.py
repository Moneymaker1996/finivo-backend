"""Light wrapper to lazily initialize a ChromaDB client and manage collections.

This avoids importing the heavy `chromadb` package at module import time.
"""
chroma_client = None


def _get_chroma_client():
    global chroma_client
    if chroma_client is not None:
        return chroma_client
    try:
        import chromadb
        chroma_client = chromadb.Client()
        return chroma_client
    except Exception:
        # Try again to raise a clearer error upstream
        chroma_client = chromadb.Client()
        return chroma_client


def get_or_create_collection(user_id: str):
    client = _get_chroma_client()
    collection_name = f"user_{user_id}_memory"
    try:
        return client.get_collection(name=collection_name)
    except Exception:
        return client.create_collection(name=collection_name)
