from .client import OllamaClient, OllamaClientError, OllamaConnectionError, OllamaModelNotFoundError
from .schemas import LoanExtractionResult, ExtractedField, OtherChargeField
from .extractor import DocumentExtractor, clean_numeric_value

def extract_loan_details(pages: list[dict]) -> LoanExtractionResult:
    """
    Orchestrates extraction from raw page texts using the local Ollama LLM.
    Returns: LoanExtractionResult object
    """
    extractor = DocumentExtractor()
    return extractor.extract_from_pages(pages)
