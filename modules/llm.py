import os
import logging
from typing import Optional, Any
import config

logger = logging.getLogger("truthguard.llm")

def get_llm():
    """
    Returns an initialized LangChain ChatModel instance based on config.LLM_PROVIDER.
    Supports 'gemini' (ChatGoogleGenerativeAI) and 'groq' (ChatGroq).
    If keys are absent or invalid, logs a warning and returns None to allow deterministic fallback.
    """
    provider = (config.LLM_PROVIDER or "gemini").lower()
    
    if provider == "groq":
        api_key = config.GROQ_API_KEY or os.getenv("GROQ_API_KEY", "")
        if not api_key or "your_groq" in api_key.lower():
            logger.warning("Groq API key not provided or placeholder. Using deterministic verification engine.")
            return None
        try:
            from langchain_groq import ChatGroq
            return ChatGroq(
                model=config.GROQ_MODEL or "llama-3.3-70b-versatile",
                groq_api_key=api_key,
                temperature=0.0
            )
        except Exception as e:
            logger.error(f"Failed to initialize ChatGroq: {e}")
            return None

    # Default to Gemini
    api_key = config.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
    if not api_key or "your_gemini" in api_key.lower() or api_key.startswith("AQ."):
        logger.info("Using TruthGuard deterministic verification engine (requires standard 'AIzaSy...' Gemini API key).")
        return None
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=config.GEMINI_MODEL or "gemini-1.5-flash",
            google_api_key=api_key,
            temperature=0.0
        )
    except Exception as e:
        logger.error(f"Failed to initialize ChatGoogleGenerativeAI: {e}")
        return None

