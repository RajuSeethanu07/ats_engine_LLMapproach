from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MODEL = "text-embedding-3-small"

# -----------------------------
# GLOBAL CACHE (CRITICAL)
# -----------------------------
_embedding_cache = {}


# -----------------------------
# NORMALIZE
# -----------------------------
def normalize(text: str) -> str:
    return str(text or "").strip().lower()


# -----------------------------
# SINGLE EMBEDDING (CACHED)
# -----------------------------
def get_embedding(text: str):
    """
    Convert text → vector embedding (with caching)
    """

    if not text:
        return None

    key = normalize(text)

    # ✅ CACHE HIT
    if key in _embedding_cache:
        return _embedding_cache[key]

    try:
        response = client.embeddings.create(
            model=MODEL,
            input=key
        )

        vector = response.data[0].embedding

        # ✅ STORE IN CACHE
        _embedding_cache[key] = vector

        return vector

    except Exception as e:
        print(f"❌ Embedding error for '{text}':", e)
        return None


# -----------------------------
# BATCH EMBEDDING (CACHED)
# -----------------------------
def get_embeddings_batch(texts: list):
    """
    Batch embedding with caching (VERY FAST)
    """

    if not texts:
        return []

    results = []
    to_fetch = []
    fetch_indices = []

    # -----------------------------
    # SPLIT CACHE vs API
    # -----------------------------
    for i, text in enumerate(texts):
        key = normalize(text)

        if key in _embedding_cache:
            results.append(_embedding_cache[key])
        else:
            results.append(None)
            to_fetch.append(key)
            fetch_indices.append(i)

    # -----------------------------
    # FETCH MISSING EMBEDDINGS
    # -----------------------------
    if to_fetch:
        try:
            response = client.embeddings.create(
                model=MODEL,
                input=to_fetch
            )

            for i, emb_obj in enumerate(response.data):
                vector = emb_obj.embedding
                key = to_fetch[i]

                # store in cache
                _embedding_cache[key] = vector

                # place in correct position
                results[fetch_indices[i]] = vector

        except Exception as e:
            print("❌ Batch embedding error:", e)

    # Replace any None with safe fallback
    return [vec if vec is not None else [0.0] * 1536 for vec in results]