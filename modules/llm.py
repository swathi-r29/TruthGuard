"""
TruthGuard LLM Provider
=======================
Returns a cached LangChain ChatModel instance via functools.lru_cache.

The cache key is (provider, model_name, temperature), so switching
LLM_PROVIDER in .env and calling reset_llm_cache() is fully supported
without freezing on the first provider that was initialised.

Supports:
  - 'gemini'  — ChatGoogleGenerativeAI
  - 'groq'    — ChatGroq
  - 'ollama'  — ChatOllama  (100% local / offline)

If the key/service is unavailable, returns None so the deterministic
fallback engine takes over in synthesizer_node and critic_node.
"""

import os
import logging
import functools
from typing import Optional

import config

logger = logging.getLogger("truthguard.llm")


# ---------------------------------------------------------------------------
# Internal cached factory — keyed on (provider, model_name, temperature)
# ---------------------------------------------------------------------------

@functools.lru_cache(maxsize=8)
def _build_llm(provider: str, model_name: str, temperature: float):
    """
    Creates and returns a LangChain ChatModel for the given parameters.
    Results are cached by functools.lru_cache, so the same combination of
    (provider, model_name, temperature) always returns the same instance.

    Switching the provider in .env takes effect immediately after calling
    reset_llm_cache(), which clears the lru_cache.
    """
    if provider == "ollama":
        try:
            from langchain_ollama import ChatOllama
            instance = ChatOllama(
                model=model_name,
                base_url=config.OLLAMA_BASE_URL or "http://localhost:11434",
                temperature=temperature,
            )
            logger.info("LLM cached instance created: ChatOllama (model=%s)", model_name)
            return instance
        except Exception as e:
            logger.warning(
                "Ollama local service not reachable or failed: %s. "
                "Falling back to deterministic engine.", e
            )
            return None

    if provider == "groq":
        api_key = config.GROQ_API_KEY or os.getenv("GROQ_API_KEY", "")
        if not api_key or "your_groq" in api_key.lower():
            logger.warning(
                "Groq API key not provided or placeholder. "
                "Using deterministic verification engine."
            )
            return None
        try:
            from langchain_groq import ChatGroq
            instance = ChatGroq(
                model=model_name,
                groq_api_key=api_key,
                temperature=temperature,
            )
            logger.info("LLM cached instance created: ChatGroq (model=%s)", model_name)
            return instance
        except Exception as e:
            logger.error("Failed to initialize ChatGroq: %s", e)
            return None

    # Default: Gemini
    api_key = config.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
    if not api_key or "your_gemini" in api_key.lower() or api_key.startswith("AQ."):
        logger.info(
            "Using TruthGuard deterministic verification engine "
            "(requires standard 'AIzaSy...' Gemini API key)."
        )
        return None
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        instance = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=temperature,
        )
        logger.info(
            "LLM cached instance created: ChatGoogleGenerativeAI (model=%s)", model_name
        )
        return instance
    except Exception as e:
        logger.error("Failed to initialize ChatGoogleGenerativeAI: %s", e)
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_llm():
    """
    Returns the cached LangChain ChatModel for the current config.

    Resilience / Fallback order:
      1. Primary configured provider (Gemini or Groq).
      2. If primary is unavailable or has invalid key -> automatic fallback to Ollama (local backup).
      3. If Ollama is also unavailable -> returns None (triggers offline deterministic engine).
    """
    provider = (os.getenv("LLM_PROVIDER") or config.LLM_PROVIDER or "gemini").lower()

    # 1. Primary provider
    if provider == "ollama":
        model_name = os.getenv("OLLAMA_MODEL") or config.OLLAMA_MODEL or "llama3.2:3b"
        return _build_llm("ollama", model_name, 0.0)
    elif provider == "groq":
        model_name = os.getenv("GROQ_MODEL") or config.GROQ_MODEL or "llama-3.3-70b-versatile"
        primary = _build_llm("groq", model_name, 0.0)
        if primary is not None:
            return primary
    else:  # Gemini (default)
        model_name = os.getenv("GEMINI_MODEL") or config.GEMINI_MODEL or "gemini-1.5-flash"
        primary = _build_llm("gemini", model_name, 0.0)
        if primary is not None:
            return primary

    # 2. Automatic backup fallback: Ollama (local, offline, free)
    ollama_model = os.getenv("OLLAMA_MODEL") or config.OLLAMA_MODEL or "llama3.2:3b"
    logger.info(
        "Primary LLM (%s) unavailable. Engaging local Ollama (%s) as backup.",
        provider,
        ollama_model,
    )
    backup = _build_llm("ollama", ollama_model, 0.0)
    if backup is not None:
        return backup

    # 3. Deterministic engine fallback
    logger.info(
        "Ollama backup also unavailable. Falling back to TruthGuard deterministic verification engine."
    )
    return None


def reset_llm_cache() -> None:
    """
    Clear the lru_cache so the next get_llm() call re-initialises the client.

    Call this when:
      - LLM_PROVIDER changes at runtime (e.g. switching from gemini to ollama)
      - API keys are rotated
      - Tests need a clean slate
    """
    _build_llm.cache_clear()
    logger.info("LLM lru_cache cleared — will re-initialise on next get_llm() call.")
