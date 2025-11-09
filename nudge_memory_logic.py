# memory.py
"""
ChromaDB integration for user memory storage and semantic search.
Provides functions to store, update, and search user memory documents with embeddings.
"""
import os
import logging
from fastapi import APIRouter, HTTPException, Body, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from utils.impulse_engine import scan_impulse_triggers
from routers.memory import run_earn_persuasion

# Lazy-loaded chroma/embedder
chroma_client = None
embedder = None
collection = None


def _init_chroma():
    global chroma_client, embedder, collection
    if chroma_client is not None and embedder is not None and collection is not None:
        return
    try:
        import chromadb
        from chromadb.config import Settings  # noqa: F401
        from sentence_transformers import SentenceTransformer

        chroma_client = chromadb.PersistentClient(path="chroma_storage")
        collection = chroma_client.get_or_create_collection(name="finivo_memory")
        embedder = SentenceTransformer("all-MiniLM-L6-v2")
        logging.basicConfig(filename='memory_debug.log', level=logging.INFO, format='%(asctime)s %(message)s')
    except Exception as e:
        logging.exception('Chroma init failed: %s', e)
        raise

# Typing imports for completeness
from typing import Optional, Union, List, Dict, Any

# --- Embedding-powered ChromaDB persistent client setup and memory functions ---


def store_memory(user_id: int, memory: str, timestamp=None):
    # Ensure chroma and embedder are initialized lazily
    _init_chroma()

    print("store_memory called")
    from datetime import datetime
    if timestamp is None:
        timestamp = datetime.utcnow().isoformat()
    # Check for duplicate: exact same content for the same user
    existing = collection.get(
        where={"user_id": user_id},
        include=["documents"]
    )
    if existing and "documents" in existing:
        user_docs = existing["documents"]
        if user_docs and any(doc == memory for doc in user_docs):
            print(f"Duplicate memory detected for user {user_id}, skipping add.")
            logging.info(f"Duplicate memory detected for user {user_id}, skipping add: {memory}")
            return  # Skip adding duplicate
    embedding = embedder.encode([memory]).tolist()  # List of lists
    log_msg = f"\n📦 Storing memory: {memory}\n🧠 Embedding: {embedding}\nUser ID: {user_id}\nTimestamp: {timestamp}\n"
    print(log_msg)
    logging.info(log_msg)
    collection.add(
        documents=[memory],
        metadatas=[{"user_id": user_id, "timestamp": timestamp}],
        ids=[f"user-{user_id}-memory-{collection.count() + 1}"],
        embeddings=embedding
    )
    # After adding memory to ChromaDB
    from uuid import uuid4
    from datetime import datetime
    print("🔍 Stored memory in ChromaDB:")
    print("Content:", memory)
    print("Timestamp:", datetime.now().isoformat())
    print("User ID:", user_id)
    print("Collection Name:", "finivo_memory")
    print("Memory ID:", str(uuid4()))
    logging.info(f"Stored memory in ChromaDB - Content: {memory}, Timestamp: {datetime.now().isoformat()}, User ID: {user_id}, Collection Name: finivo_memory")


def search_memory(query: str, n_results: int = 5):
    _init_chroma()

    print("search_memory called")
    query_embedding = embedder.encode([query]).tolist()
    print("🔍 Query embedding:", query_embedding)
    logging.info(f"🔍 Query embedding: {query_embedding}")
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=n_results * 2  # Fetch more to ensure uniqueness
    )
    # Deduplicate results by content
    seen = set()
    unique_docs = []
    for doc in results["documents"][0]:
        if doc not in seen:
            unique_docs.append(doc)
            seen.add(doc)
        if len(unique_docs) >= n_results:
            break
    print("📄 Unique search result:", unique_docs)
    logging.info(f"📄 Unique search result: {unique_docs}")
    return [unique_docs]


def semantic_search_recent_memories(user_id: int, query: str, min_similarity: float = 0.8, days: int = 30, n_results: int = 5):
    _init_chroma()

    from datetime import datetime, timedelta
    query_embedding = embedder.encode([query]).tolist()
    # Calculate cutoff date
    cutoff = datetime.utcnow() - timedelta(days=days)
    # Query for recent memories only
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=n_results * 2,
        where={"user_id": user_id},
        include=["metadatas", "documents", "distances"]
    )
    filtered = []
    for doc, meta, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
        mem_time = meta.get("timestamp")
        if mem_time:
            try:
                mem_time = datetime.fromisoformat(mem_time)
            except Exception:
                continue
            if mem_time < cutoff:
                continue
        similarity = 1 - dist
        if similarity >= min_similarity:
            filtered.append((doc, similarity))
        if len(filtered) >= n_results:
            break
    return filtered
# Note: functions below will initialize chroma/embedder lazily when called

router = APIRouter()

class NudgeRequest(BaseModel):
    item_name: str = ""
    mood: str = ""
    pattern: str = ""
    urgency: bool = False
    last_purchase_days: int = None
    situation: str = ""
    explanation: str = ""
    spending_intent: str = ""

@router.post("/nudge/{user_id}")
async def nudge_user(user_id: int, body: NudgeRequest, db: Session = Depends(get_db)):
    print("NUDGE ENDPOINT HIT")
    from utils.plan_features import get_user_plan, get_plan_features
    plan = get_user_plan(user_id, db)
    plan_features = get_plan_features(plan)

    # Merge NLP and structured logic: always run impulse and persuasion
    payload = body.dict()
    impulse_result = scan_impulse_triggers(payload)
    tone = plan_features.get("ai_tone", "basic")
    earn_result = run_earn_persuasion(body, tone)

    # Nudge limit enforcement (example for Essential plan)
    nudge_limit = plan_features.get("nudge_limit")
    nudge_count = None
    if nudge_limit:
        from models import NudgeLog
        from datetime import datetime
        now = datetime.utcnow()
        start_of_month = datetime(now.year, now.month, 1)
        nudge_count = db.query(NudgeLog).filter(
            NudgeLog.user_id == user_id,
            NudgeLog.timestamp >= start_of_month
        ).count()
        if nudge_count >= nudge_limit:
            return {
                "plan": plan,
                "message": f"[{plan.title()}] Monthly nudge limit reached. Consider upgrading for more support.",
                "impulse": impulse_result,
                "earn": earn_result,
                "debug": {"nudge_count": nudge_count, "nudge_limit": nudge_limit}
            }

    # Compose nudge message
    if impulse_result["is_impulsive"]:
        persuasion_mode = True
        nudge_message = earn_result.get("nudge") or "This seems impulsive. You might want to wait before buying."
    else:
        persuasion_mode = False
        nudge_message = plan_features.get("fallback_responses", ["All clear. Just a gentle reminder to stay mindful."])[0]

    # Log the nudge (optional, if you want to keep history)
    # ...existing code for logging...

    # Always return full context
    response = {
        "plan": plan,
        "plan_features": plan_features,
        "impulse": impulse_result,
        "earn": earn_result,
        "persuasion_mode": persuasion_mode,
        "nudge_message": nudge_message,
        "payload": payload,
        "debug": {
            "triggered_flags": impulse_result["triggered_flags"],
            "reasoning": impulse_result["debug"],
            "nudge_count": nudge_count,
            "nudge_limit": nudge_limit
        }
    }
    print("[NUDGE RESPONSE]", response)
    return response
