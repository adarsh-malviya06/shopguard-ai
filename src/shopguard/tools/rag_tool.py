"""RAG Knowledge Tool — ChromaDB + Sentence Transformers.

Uses all-MiniLM-L6-v2 embeddings and persistent ChromaDB storage.
Implements real semantic retrieval — NOT keyword search.
"""

from __future__ import annotations
import hashlib
import re
from pathlib import Path
from typing import Optional

from src.shopguard.config import settings
from src.shopguard.logging_config import logger

# --------------------------------------------------------------------------- #
# Synonym Expansion                                                             #
# --------------------------------------------------------------------------- #

SYNONYM_MAP: dict[str, list[str]] = {
    "refund":       ["money back", "reimbursement", "return money", "credit"],
    "return":       ["send back", "returning product", "exchange"],
    "cancel":       ["cancellation", "stop order", "abort order"],
    "delay":        ["late", "slow", "behind schedule", "overdue", "not arrived"],
    "damaged":      ["broken", "defective", "faulty", "torn", "scratched"],
    "missing":      ["lost", "not delivered", "absent", "not received"],
    "shipping":     ["delivery", "dispatch", "courier", "tracking"],
    "policy":       ["rules", "guidelines", "procedure", "terms"],
    "eligible":     ["qualify", "allowed", "permitted", "valid"],
}


def expand_query(query: str) -> str:
    """Expand query with synonyms to improve recall."""
    words = query.lower().split()
    expansions = []
    for word in words:
        for key, synonyms in SYNONYM_MAP.items():
            if word.startswith(key[:5]) and key not in expansions:
                expansions.extend(synonyms[:2])
    if expansions:
        return query + " " + " ".join(expansions[:6])
    return query


# --------------------------------------------------------------------------- #
# Document Loading & Chunking                                                   #
# --------------------------------------------------------------------------- #

def _load_policy_documents() -> list[dict]:
    """Load policy content from knowledge_base/policies.py and .md files."""
    from knowledge_base.policies import (
        REFUND_POLICY, SHIPPING_POLICY, CANCELLATION_POLICY, SUPPORT_PROCEDURES
    )
    raw_docs = [
        {"content": REFUND_POLICY,        "source": "refund_policy",        "policy_type": "refund"},
        {"content": SHIPPING_POLICY,      "source": "shipping_policy",      "policy_type": "shipping"},
        {"content": CANCELLATION_POLICY,  "source": "cancellation_policy",  "policy_type": "cancellation"},
        {"content": SUPPORT_PROCEDURES,   "source": "support_procedures",   "policy_type": "support"},
    ]
    chunks = []
    for doc in raw_docs:
        chunks.extend(_chunk_document(doc["content"], doc["source"], doc["policy_type"]))
    return chunks


def _chunk_document(text: str, source: str, policy_type: str, chunk_size: int = 400) -> list[dict]:
    """Split document into semantic chunks by heading or paragraph."""
    # Split on markdown headings first
    sections = re.split(r"\n(?=##? )", text.strip())
    chunks = []
    for i, section in enumerate(sections):
        section = section.strip()
        if not section:
            continue
        # Further split long sections by paragraph
        paragraphs = [p.strip() for p in section.split("\n\n") if p.strip()]
        current_chunk = ""
        chunk_idx = 0
        for para in paragraphs:
            if len(current_chunk) + len(para) < chunk_size:
                current_chunk = (current_chunk + "\n\n" + para).strip()
            else:
                if current_chunk:
                    chunk_id = f"{source}_{i}_{chunk_idx}"
                    chunks.append({
                        "id":          chunk_id,
                        "content":     current_chunk,
                        "source":      source,
                        "policy_type": policy_type,
                        "doc_hash":    hashlib.md5(current_chunk.encode()).hexdigest()[:8],
                    })
                    chunk_idx += 1
                current_chunk = para
        if current_chunk:
            chunk_id = f"{source}_{i}_{chunk_idx}"
            chunks.append({
                "id":          chunk_id,
                "content":     current_chunk,
                "source":      source,
                "policy_type": policy_type,
                "doc_hash":    hashlib.md5(current_chunk.encode()).hexdigest()[:8],
            })
    return chunks


# --------------------------------------------------------------------------- #
# ChromaDB Collection                                                           #
# --------------------------------------------------------------------------- #

_collection = None  # Module-level singleton


def _get_collection():
    """Get or create the ChromaDB collection (lazy init)."""
    global _collection
    if _collection is not None:
        return _collection
    import chromadb
    from chromadb.utils import embedding_functions

    client = chromadb.PersistentClient(path=str(settings.CHROMA_PERSIST_DIR))
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    _collection = client.get_or_create_collection(
        name="shopguard_policies",
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )
    return _collection


# --------------------------------------------------------------------------- #
# Public Functions                                                              #
# --------------------------------------------------------------------------- #

def seed_knowledge_base(force: bool = False) -> dict:
    """Load and index all policy documents into ChromaDB.

    Idempotent: skips documents that are already indexed (by chunk ID).
    Set force=True to clear and re-index everything.
    """
    col = _get_collection()

    if force:
        # Clear existing entries
        existing = col.get()
        if existing["ids"]:
            col.delete(ids=existing["ids"])
            logger.info("Cleared %d existing RAG chunks.", len(existing["ids"]))

    chunks = _load_policy_documents()
    if not chunks:
        logger.warning("No policy documents found to index.")
        return {"indexed": 0, "skipped": 0}

    # Determine which chunks need to be added
    existing_ids = set(col.get()["ids"])
    new_chunks = [c for c in chunks if c["id"] not in existing_ids]

    if not new_chunks:
        logger.info("Knowledge base already up-to-date (%d chunks).", len(existing_ids))
        return {"indexed": 0, "skipped": len(chunks)}

    col.add(
        ids=[c["id"] for c in new_chunks],
        documents=[c["content"] for c in new_chunks],
        metadatas=[{
            "source":      c["source"],
            "policy_type": c["policy_type"],
            "doc_hash":    c["doc_hash"],
        } for c in new_chunks],
    )
    logger.info("Seeded %d new RAG chunks into ChromaDB.", len(new_chunks))
    return {"indexed": len(new_chunks), "skipped": len(existing_ids)}


def retrieve_policy(query: str, top_k: int = 4, threshold: float = 0.45) -> list[dict]:
    """Retrieve relevant policy chunks for a query.

    Returns empty list and fails closed if collection is empty or below threshold.
    threshold is the maximum cosine DISTANCE (lower = more similar).
    """
    col = _get_collection()

    # Fail closed if collection is empty
    count = col.count()
    if count == 0:
        logger.warning("RAG collection is empty — failing closed.")
        return []

    expanded = expand_query(query)
    results = col.query(
        query_texts=[expanded],
        n_results=min(top_k, count),
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        if dist <= threshold:
            chunks.append({
                "content":     doc,
                "source":      meta.get("source", "unknown"),
                "policy_type": meta.get("policy_type", ""),
                "distance":    round(dist, 4),
                "similarity":  round(1 - dist, 4),
            })

    if not chunks:
        logger.warning("No RAG chunks above threshold (%.2f) for query: %s", threshold, query[:80])
    return chunks


def get_policy_sources() -> list[str]:
    """Return list of distinct source names currently indexed."""
    col = _get_collection()
    data = col.get(include=["metadatas"])
    sources = list({m.get("source", "") for m in data["metadatas"] if m})
    return sorted(sources)


def collection_health() -> dict:
    """Return basic health stats for the ChromaDB collection."""
    col = _get_collection()
    count = col.count()
    sources = get_policy_sources()
    return {
        "status":        "ready" if count > 0 else "empty",
        "total_chunks":  count,
        "indexed_sources": sources,
    }
