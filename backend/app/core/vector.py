"""
Qdrant vector store with Sentence Transformers embeddings for policy RAG.
"""
import logging
from typing import Optional
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)
from sentence_transformers import SentenceTransformer
from app.config import get_settings
import uuid

logger = logging.getLogger(__name__)

_qdrant_client: Optional[QdrantClient] = None
_embedder: Optional[SentenceTransformer] = None

EMBEDDING_DIM = 384
COLLECTIONS = {
    "security_policies": EMBEDDING_DIM,
    "compliance_policies": EMBEDDING_DIM,
    "financial_policies": EMBEDDING_DIM,
}


def get_qdrant() -> QdrantClient:
    """Get or create a Qdrant client singleton."""
    global _qdrant_client
    if _qdrant_client is None:
        settings = get_settings()
        _qdrant_client = QdrantClient(url=settings.qdrant_url)
        logger.info(f"Qdrant client connected to {settings.qdrant_url}")
    return _qdrant_client


def get_embedder() -> SentenceTransformer:
    """Get or create a SentenceTransformer singleton."""
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("SentenceTransformer (all-MiniLM-L6-v2) loaded")
    return _embedder


def init_collections():
    """Initialize Qdrant collections if they don't exist."""
    client = get_qdrant()
    existing = {c.name for c in client.get_collections().collections}

    for name, dim in COLLECTIONS.items():
        if name not in existing:
            client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )
            logger.info(f"Created Qdrant collection: {name}")
        else:
            logger.info(f"Qdrant collection already exists: {name}")


def embed_text(text: str) -> list[float]:
    """Generate an embedding vector for a text string."""
    embedder = get_embedder()
    return embedder.encode(text).tolist()


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate embedding vectors for multiple text strings."""
    embedder = get_embedder()
    return embedder.encode(texts).tolist()


def upsert_policy(
    collection: str,
    policy_id: str,
    title: str,
    content: str,
    metadata: Optional[dict] = None,
):
    """Add or update a policy document in the vector store."""
    client = get_qdrant()
    vector = embed_text(f"{title}\n{content}")

    payload = {
        "policy_id": policy_id,
        "title": title,
        "content": content,
        **(metadata or {}),
    }

    point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, policy_id))

    client.upsert(
        collection_name=collection,
        points=[
            PointStruct(
                id=point_id,
                vector=vector,
                payload=payload,
            )
        ],
    )
    logger.info(f"Upserted policy '{title}' into {collection}")


def search_policies(
    collection: str,
    query: str,
    top_k: int = 5,
    score_threshold: float = 0.3,
    category_filter: Optional[str] = None,
) -> list[dict]:
    """
    Semantic search for policies in a Qdrant collection.
    Returns top-k results with their relevance scores.
    """
    client = get_qdrant()
    query_vector = embed_text(query)

    search_filter = None
    if category_filter:
        search_filter = Filter(
            must=[
                FieldCondition(
                    key="category",
                    match=MatchValue(value=category_filter),
                )
            ]
        )

    results = client.search(
        collection_name=collection,
        query_vector=query_vector,
        limit=top_k,
        score_threshold=score_threshold,
        query_filter=search_filter,
    )

    return [
        {
            "id": str(hit.id),
            "score": hit.score,
            "title": hit.payload.get("title", ""),
            "content": hit.payload.get("content", ""),
            "policy_id": hit.payload.get("policy_id", ""),
            **{
                k: v
                for k, v in hit.payload.items()
                if k not in ("title", "content", "policy_id")
            },
        }
        for hit in results
    ]


def check_vector_health() -> bool:
    """Check if the Qdrant service is healthy."""
    try:
        client = get_qdrant()
        client.get_collections()
        return True
    except Exception as e:
        logger.error(f"Qdrant health check failed: {e}")
        return False
