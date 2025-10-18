import chromadb

# Use an in-memory client on Render (avoid persistent storage)
try:
    chroma_client = chromadb.Client()
except Exception:
    chroma_client = chromadb.Client()


def get_or_create_collection(user_id: str):
    collection_name = f"user_{user_id}_memory"
    try:
        return chroma_client.get_collection(name=collection_name)
    except Exception:
        return chroma_client.create_collection(name=collection_name)
