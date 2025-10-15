# memory.py
"""
ChromaDB integration for user memory storage and semantic search.
Provides functions to store, update, and search user memory documents with embeddings.
"""
import chromadb
from chromadb.config import Settings
import os
import logging
from fastapi import APIRouter, HTTPException, Body, Depends
from pydantic import BaseModel
from schemas import NudgeRequest
from database import get_db
from utils.plan_features import get_plan_features, get_user_plan
from sqlalchemy.orm import Session
from models import User

# Typing imports for completeness
from typing import Optional, Union, List, Dict, Any

# --- Embedding-powered ChromaDB persistent client setup and memory functions ---
try:
    from sentence_transformers import SentenceTransformer

    # Initialize ChromaDB persistent client using new API (v1.0+)
    chroma_client = chromadb.PersistentClient(path="chroma_storage")
    collection = chroma_client.get_or_create_collection(name="finivo_memory")

    # Load a local embedding model (e.g., all-MiniLM-L6-v2)
    embedder = SentenceTransformer("all-MiniLM-L6-v2")

    # Setup logging
    logging.basicConfig(filename='memory_debug.log', level=logging.INFO, format='%(asctime)s %(message)s')

    def store_memory(user_id: int, memory: str, timestamp=None):
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
        print("search_memory called")
        """Perform semantic search over user memory documents and return unique results only."""
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
except Exception as e:
    print(f"ChromaDB persistent client setup failed: {e}")

router = APIRouter()




@router.post("/nudge/{user_id}")
async def nudge_user(user_id: int, request: NudgeRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"error": "User not found"}

    plan = get_user_plan(user_id, db)
    if not plan:
        return {"error": "User plan not found"}

    plan_features = get_plan_features(plan)

    # Always run impulse and earn logic
    payload = request.dict()
    from utils.impulse_engine import scan_impulse_triggers
    from routers.memory import run_earn_persuasion
    impulse_result = scan_impulse_triggers(payload)
    tone = plan_features.get("ai_tone", "basic")
    earn_result = run_earn_persuasion(request, tone)

    # Compose nudge message based on plan tier and impulse
    if impulse_result["is_impulsive"]:
        persuasion_mode = True
        if plan == "essential":
            nudge_message = (
                "This feels impulsive. Want to pause and revisit tomorrow? I can remind you if you want."
            )
        elif plan == "prestige":
            nudge_message = (
                "Impulse detected! Let's take a breather and reflect for 24 hours. If you want, I can help you set a reminder or talk through your reasons."
            )
        elif plan == "elite":
            nudge_message = (
                "I sense this is an impulse purchase. Let's dig deeper: Is this truly aligned with your goals, or is it a fleeting urge? I can bookmark this and check in with you tomorrow, or we can discuss your motivations in detail."
            )
        else:
            nudge_message = "This seems impulsive. You might want to wait before buying."
    else:
        persuasion_mode = False
        nudge_message = plan_features.get("fallback_responses", ["All clear. Just a gentle reminder to stay mindful."])[0]

    # Build impulse summary (no debug info)
    impulse_summary = {
        "total_triggers": impulse_result["total_triggers"],
        "is_impulsive": impulse_result["is_impulsive"],
        "triggered_flags": impulse_result["triggered_flags"]
    }

    # Remove fallback responses from response if impulse detected
    response = {
        "plan": plan,
        "plan_features": plan_features if not impulse_result["is_impulsive"] else {k: v for k, v in plan_features.items() if k != "fallback_responses"},
        "impulse": impulse_summary,
        "earn": earn_result,
        "persuasion_mode": persuasion_mode,
        "nudge_message": nudge_message,
        "payload": payload
    }
    print("[NUDGE RESPONSE]", response)
    return response
