import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

def get_config_val(key: str, default: str = "") -> str:
    val = os.getenv(key, "")
    return val if val else default

# LLM Configuration: 'gemini', 'groq', or 'ollama'
LLM_PROVIDER = get_config_val("LLM_PROVIDER", "gemini").lower()

# Gemini Config
GEMINI_API_KEY = get_config_val("GEMINI_API_KEY", "")
GEMINI_MODEL = get_config_val("GEMINI_MODEL", "gemini-1.5-flash")

# Groq Config
GROQ_API_KEY = get_config_val("GROQ_API_KEY", "")
GROQ_MODEL = get_config_val("GROQ_MODEL", "llama-3.3-70b-versatile")

# Ollama Config (Local 100% Free / Offline)
OLLAMA_BASE_URL = get_config_val("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = get_config_val("OLLAMA_MODEL", "llama3")

# OCR Configuration
TESSERACT_CMD = get_config_val("TESSERACT_CMD", "")

# Chroma Vector Store & Persistence
CHROMA_PERSIST_DIR = BASE_DIR / "chroma_db"
CHROMA_PERSIST_DIR.mkdir(exist_ok=True)

# Uploads
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

# Debugging
DEBUG = get_config_val("DEBUG", "false").lower() == "true"

# Ensure pytesseract is configured if custom command path is provided
if TESSERACT_CMD:
    try:
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
    except Exception:
        pass
