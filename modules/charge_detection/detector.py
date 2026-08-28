import re
from typing import List, Dict, Any
from modules.ai_extraction.schemas import LoanExtractionResult
from .rules import KEYWORDS_MAPPING
from .classifier import classify_charge

def detect_charges(extracted_result: LoanExtractionResult, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Combines AI-extracted fields and keyword scanning on raw pages to create
    a complete list of standardized financial charges.
    """
    detected = []
    processed_keys = set()
    
    # 1. Process standard fields from the AI Extraction
    schema_fields = LoanExtractionResult.model_fields.keys()
    
    for field_name in schema_fields:
        if field_name in ['other_charges', 'lender_name', 'borrower_name', 'document_type']:
            continue
            
        field_data = getattr(extracted_result, field_name)
        if field_data and field_data.value is not None:
            canonical_name = field_name
            original_name = field_name.replace("_", " ").title()
            unit = field_data.unit or ("percent" if "percent" in field_name else "currency")
            
            # Unify processing_fee_percentage with processing_fee if absolute value is missing
            if field_name == "processing_fee_percentage":
                processed_keys.add("processing_fee")
                processed_keys.add("processing_fee_percentage")
                if getattr(extracted_result, "processing_fee", None) is None or getattr(extracted_result, "processing_fee").value is None:
                    canonical_name = "processing_fee"
                    original_name = "Processing Fee"
                    unit = "percent"
            elif field_name == "processing_fee":
                processed_keys.add("processing_fee")
                processed_keys.add("processing_fee_percentage")
            else:
                processed_keys.add(field_name)
                
            if canonical_name == "gst_tax_references":
                original_name = "GST"
                
            classification = classify_charge(canonical_name)
            
            # Determine mandatory vs conditional
            is_mandatory = classification in ["BASE_COST", "ADDITIONAL_COST", "TAX"]
            is_conditional = classification in ["CONDITIONAL_COST", "PENALTY"]
            
            detected.append({
                "canonical_name": canonical_name,
                "original_name": original_name,
                "value": field_data.value,
                "unit": unit,
                "basis": field_data.basis or "flat",
                "page": field_data.page,
                "evidence": field_data.evidence or "Found in extracted terms.",
                "classification": classification,
                "is_mandatory": is_mandatory,
                "is_conditional": is_conditional,
                "source": "ai_extraction"
            })
            
    # 2. Process other charges array
    for charge in extracted_result.other_charges:
        if charge.value is not None:
            name_normalized = charge.name.lower().replace(" ", "_")
            processed_keys.add(name_normalized)
            classification = classify_charge(name_normalized)
            
            is_mandatory = classification in ["BASE_COST", "ADDITIONAL_COST", "TAX"]
            is_conditional = classification in ["CONDITIONAL_COST", "PENALTY"]
            
            detected.append({
                "canonical_name": name_normalized,
                "original_name": charge.name,
                "value": charge.value,
                "unit": charge.unit or "currency",
                "basis": charge.basis or "flat",
                "page": charge.page or 1,
                "evidence": charge.evidence or "Found in other charges.",
                "classification": classification,
                "is_mandatory": is_mandatory,
                "is_conditional": is_conditional,
                "source": "ai_extraction"
            })
            
    # 3. Hybrid keyword check: Scan text for keywords not extracted by the LLM
    for canonical_name, patterns in KEYWORDS_MAPPING.items():
        # Skip if already successfully extracted by LLM
        if canonical_name in processed_keys or any(d["canonical_name"] == canonical_name for d in detected):
            continue
            
        # Scan page-by-page
        for page in pages:
            text = page.get("text", "")
            page_num = page.get("page_number", 1)
            
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    # Found a keyword reference that wasn't extracted with a value
                    classification = classify_charge(canonical_name)
                    is_mandatory = classification in ["BASE_COST", "ADDITIONAL_COST", "TAX"]
                    is_conditional = classification in ["CONDITIONAL_COST", "PENALTY"]
                    
                    # Extract surrounding sentence/context
                    start_idx = max(0, match.start() - 40)
                    end_idx = min(len(text), match.end() + 80)
                    context_snippet = text[start_idx:end_idx].strip()
                    context_sentence = f"...{context_snippet}..."
                    
                    detected.append({
                        "canonical_name": canonical_name,
                        "original_name": canonical_name.replace("_", " ").title(),
                        "value": None, # Mentioned but no value known
                        "unit": "unknown",
                        "basis": "unknown",
                        "page": page_num,
                        "evidence": context_sentence,
                        "classification": classification,
                        "is_mandatory": is_mandatory,
                        "is_conditional": is_conditional,
                        "source": "keyword_reference"
                    })
                    # Avoid adding duplicate references for the same charge type
                    break
            else:
                continue
            break # break outer loop if already added for this canonical name
            
    return detected
