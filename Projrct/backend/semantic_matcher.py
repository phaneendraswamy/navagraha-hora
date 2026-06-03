from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from backend.config import get_settings


@lru_cache
def get_embedding_model() -> SentenceTransformer:
    return SentenceTransformer(get_settings().embedding_model)


def text_list_similarity(query: str, documents: list[str]) -> list[float]:
    if not documents:
        return []
    try:
        model = get_embedding_model()
        vectors = model.encode([query] + documents, normalize_embeddings=True)
        scores = cosine_similarity(np.array(vectors[:1]), np.array(vectors[1:]))[0]
    except Exception:
        vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        vectors = vectorizer.fit_transform([query] + documents)
        scores = cosine_similarity(vectors[:1], vectors[1:])[0]
    return [float(round(score, 4)) for score in scores]


def rank_items(query: str, items: list[dict], text_key: str, top_k: int = 5) -> list[dict]:
    docs = [item[text_key] for item in items]
    scores = text_list_similarity(query, docs)
    ranked = [{**item, "relevance_score": score} for item, score in zip(items, scores, strict=False)]
    return sorted(ranked, key=lambda item: item["relevance_score"], reverse=True)[:top_k]
