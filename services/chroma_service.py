import chromadb

chroma_client = chromadb.PersistentClient(path="./chroma_storage")

def get_or_create_collection(user_id: str):
    collection_name = f"user_{user_id}_memory"
    try:
        return chroma_client.get_collection(name=collection_name)
    except:
        return chroma_client.create_collection(name=collection_name)
