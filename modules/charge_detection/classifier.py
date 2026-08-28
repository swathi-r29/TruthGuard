from .rules import CLASSIFICATION_MAPPING

def classify_charge(canonical_name: str) -> str:
    """
    Classifies a charge name into one of the standardized financial categories:
    BASE_COST, ADDITIONAL_COST, TAX, CONDITIONAL_COST, PENALTY, OPTIONAL_COST, OTHER.
    """
    # Normalize input
    name = canonical_name.strip().lower()
    
    # Check mapping
    if name in CLASSIFICATION_MAPPING:
        return CLASSIFICATION_MAPPING[name]
        
    # Standard prefix mappings (e.g. if field is processing_fee_percentage, classify as processing_fee)
    for key, category in CLASSIFICATION_MAPPING.items():
        if name.startswith(key) or key.startswith(name):
            return category
            
    return "OTHER"
