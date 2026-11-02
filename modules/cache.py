"""
TruthGuard In-Memory Cache
==========================
Provides two lightweight, thread-safe LRU caches with no external dependencies:

  1. llm_cache  (LLMResponseCache)
     Caches LLM text completions keyed by SHA-256(prompt).
     Safe because all LLM calls use temperature=0.0 — identical prompts
     always produce identical output.
     Covers: synthesizer_node, critic_node (when LLM path is active).

  2. search_cache  (SearchCache)
     Caches ChromaDB retrieval results keyed by SHA-256(query::target_date).
     The target_date component is MANDATORY to prevent Time-Travel Query
     collisions (same question, different historical date → different evidence).

Invalidation
------------
Call ``clear_all_caches()`` whenever the corpus changes (document upload,
seed, or delete). This forces the next query to fetch fresh evidence.

Usage
-----
    from modules.cache import llm_cache, search_cache, clear_all_caches

    # -- LLM cache (synthesizer / critic) ---------------------------------
    cached = llm_cache.get_response(prompt)
    if cached is None:
        response = llm.invoke(prompt)
        llm_cache.set_response(prompt, response.content)
        cached = response.content

    # -- Search cache (retriever node) ------------------------------------
    passages = search_cache.get_passages(query, target_date)
    if passages is None:
        passages = vector_store.search_passages(query, n_results=20)
        search_cache.set_passages(query, target_date, passages)
"""

import hashlib
import logging
import threading
from collections import OrderedDict
from typing import Any, List, Optional

logger = logging.getLogger("truthguard.cache")


# ---------------------------------------------------------------------------
# Generic thread-safe LRU cache base
# ---------------------------------------------------------------------------

class _LRUCache:
    """
    Thread-safe LRU cache backed by an OrderedDict.
    Evicts the least-recently-used entry when maxsize is exceeded.
    """

    def __init__(self, maxsize: int = 256, name: str = "cache"):
        self._maxsize = maxsize
        self._name = name
        self._store: OrderedDict = OrderedDict()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def _get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._store:
                self._misses += 1
                return None
            self._store.move_to_end(key)   # mark as most-recently used
            self._hits += 1
            return self._store[key]

    def _set(self, key: str, value: Any) -> None:
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
            self._store[key] = value
            if len(self._store) > self._maxsize:
                evicted, _ = self._store.popitem(last=False)
                logger.debug("[%s] LRU evict key=%s...", self._name, evicted[:16])

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._hits = 0
            self._misses = 0
        logger.info("[%s] Cache cleared.", self._name)

    @property
    def stats(self) -> dict:
        with self._lock:
            total = self._hits + self._misses
            return {
                "name": self._name,
                "size": len(self._store),
                "maxsize": self._maxsize,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate_pct": round(self._hits / total * 100, 1) if total else 0.0,
            }

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)


# ---------------------------------------------------------------------------
# LLM Response Cache
# ---------------------------------------------------------------------------

class LLMResponseCache(_LRUCache):
    """
    Caches LLM text responses keyed by SHA-256(prompt).

    Key design note
    ---------------
    The synthesizer prompt already embeds the question + all passage content,
    and the critic prompt embeds the draft + all passage content.
    Therefore a single SHA-256 of the raw prompt string is a safe, collision-
    resistant cache key that captures the full input space.
    """

    def __init__(self, maxsize: int = 256):
        super().__init__(maxsize=maxsize, name="llm_response_cache")

    @staticmethod
    def _make_key(prompt: str) -> str:
        return hashlib.sha256(prompt.encode("utf-8")).hexdigest()

    def get_response(self, prompt: str) -> Optional[str]:
        """Return cached LLM output for *prompt*, or None on a miss."""
        key = self._make_key(prompt)
        value = self._get(key)
        if value is not None:
            logger.debug("[llm_cache] HIT  key=%s...", key[:16])
        else:
            logger.debug("[llm_cache] MISS key=%s...", key[:16])
        return value

    def set_response(self, prompt: str, response_text: str) -> None:
        """Store *response_text* as the cached output for *prompt*."""
        key = self._make_key(prompt)
        self._set(key, response_text)
        logger.debug("[llm_cache] SET  key=%s... (%d chars)", key[:16], len(response_text))


# ---------------------------------------------------------------------------
# Vector Search Cache
# ---------------------------------------------------------------------------

class SearchCache(_LRUCache):
    """
    Caches ChromaDB vector-search results keyed by SHA-256(query::target_date).

    Key design note — Time-Travel Query safety
    ------------------------------------------
    TruthGuard supports time-travel queries:
        query="What is the leave entitlement?", target_date="2023-05-10"
    must NOT collide with:
        query="What is the leave entitlement?", target_date=None

    The composite key ``f"{query.strip().lower()}::{target_date or 'latest'}"``
    guarantees a distinct hash for every (question, date) pair.
    """

    def __init__(self, maxsize: int = 128):
        super().__init__(maxsize=maxsize, name="search_cache")

    @staticmethod
    def _make_key(query: str, target_date: Optional[str]) -> str:
        # 'latest' sentinel is used when no target_date is specified
        raw = f"{query.strip().lower()}::{target_date or 'latest'}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get_passages(self, query: str, target_date: Optional[str]) -> Optional[List]:
        """Return cached passage list for *(query, target_date)*, or None on a miss."""
        key = self._make_key(query, target_date)
        value = self._get(key)
        if value is not None:
            logger.debug("[search_cache] HIT  query=%r date=%s", query[:40], target_date)
        else:
            logger.debug("[search_cache] MISS query=%r date=%s", query[:40], target_date)
        return value

    def set_passages(self, query: str, target_date: Optional[str], passages: List) -> None:
        """Store *passages* for *(query, target_date)*."""
        key = self._make_key(query, target_date)
        self._set(key, passages)
        logger.debug(
            "[search_cache] SET  query=%r date=%s -> %d passages",
            query[:40], target_date, len(passages)
        )


# ---------------------------------------------------------------------------
# Module-level singletons
# ---------------------------------------------------------------------------

#: LLM response cache — max 256 entries (synthesizer + critic combined)
llm_cache: LLMResponseCache = LLMResponseCache(maxsize=256)

#: Retrieval/search cache — max 128 entries
search_cache: SearchCache = SearchCache(maxsize=128)


# ---------------------------------------------------------------------------
# Corpus invalidation helper
# ---------------------------------------------------------------------------

def clear_all_caches() -> None:
    """
    Invalidate ALL caches.

    Must be called whenever the document corpus changes:
      - POST /api/upload      (new document ingested)
      - POST /api/seed_samples
      - DELETE /api/documents

    Clears both the search cache (stale ChromaDB results) and the LLM cache
    (answers that referenced documents now absent or amended).
    """
    search_cache.clear()
    llm_cache.clear()
    logger.info("All TruthGuard caches cleared after corpus change.")


def get_cache_stats() -> dict:
    """Return combined cache statistics for /api/health or debug endpoints."""
    return {
        "llm_cache": llm_cache.stats,
        "search_cache": search_cache.stats,
    }
