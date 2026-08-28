import re
import unicodedata

def clean_text(text: str) -> str:
    """
    Cleans extracted text by normalizing whitespace, stripping non-printable characters,
    but preserving paragraphs and sentence breaks for readability.
    """
    if not text:
        return ""
        
    # Normalize unicode characters (converting ligatures, non-breaking spaces, etc.)
    text = unicodedata.normalize('NFKC', text)
        
    # Split into lines, normalize spaces on each line, and strip trailing spaces
    cleaned_lines = []
    for line in text.splitlines():
        line_clean = re.sub(r'[ \t]+', ' ', line).strip()
        cleaned_lines.append(line_clean)
        
    cleaned = "\n".join(cleaned_lines)
    
    # Replace more than two newlines with two newlines (preserve paragraphs)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    
    # Remove control characters except tab and newline
    cleaned = "".join(ch for ch in cleaned if ch.isprintable() or ch in ['\n', '\t'])
    
    return cleaned.strip()
