import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

def get_config_val(key: str, default: str = "") -> str:
    val = os.getenv(key, "")
    if not val:
        try:
            import streamlit as st
            if hasattr(st, "secrets") and key in st.secrets:
                val = st.secrets[key]
        except Exception:
            pass
    return val if val else default

# LLM Configuration
LLM_PROVIDER = get_config_val("LLM_PROVIDER", "gemini").lower()
OLLAMA_MODEL = get_config_val("OLLAMA_MODEL", "gemma2:2b")
OLLAMA_BASE_URL = get_config_val("OLLAMA_BASE_URL", "http://localhost:11434")
GEMINI_API_KEY = get_config_val("GEMINI_API_KEY", "")
GEMINI_MODEL = get_config_val("GEMINI_MODEL", "gemini-1.5-flash")

# OCR Configuration
TESSERACT_CMD = get_config_val("TESSERACT_CMD", "")

# UI Settings
CURRENCY_SYMBOL = get_config_val("CURRENCY_SYMBOL", "₹")

# Debugging
DEBUG = get_config_val("DEBUG", "false").lower() == "true"

# Paths
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

# Ensure pytesseract is configured if custom command path is provided
if TESSERACT_CMD:
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
