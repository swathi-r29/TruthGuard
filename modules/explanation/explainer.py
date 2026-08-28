from typing import Dict, Any, Optional
from modules.ai_extraction.client import OllamaClient, OllamaClientError

EXPLAINER_SYSTEM_PROMPT = """You are a consumer finance expert. Your job is to translate complex legal or financial contract clauses into simple, friendly, one-sentence plain English for a layperson.
Do not use jargon. Focus on what it means for their wallet.
Example:
Input: 'The borrower shall be liable to pay four percent of the outstanding principal upon prepayment.'
Output: 'Closing the loan early may cost you 4% of the remaining principal balance.'
"""

TEMPLATE_EXPLANATIONS = {
    "processing_fee": "This is an upfront fee charged by the lender to process and activate your loan application.",
    "documentation_fee": "This covers administrative costs, stamp duty, or legal paperwork needed to execute the loan agreement.",
    "insurance": "An insurance cover bundled with the loan to protect against death, disability, or job loss. Check if it's optional.",
    "foreclosure_charge": "A penalty fee charged if you pay off the entire outstanding loan balance earlier than scheduled.",
    "prepayment_charge": "A fee charged if you make a part-prepayment to reduce your outstanding loan balance.",
    "late_payment_fee": "A flat fee or penalty interest charged if you miss your scheduled EMI payment date.",
    "bounce_charge": "Charged when an auto-debit (ECS/NACH) or check bounces due to insufficient funds in your bank account.",
    "default_penalty": "Extra interest charged on your outstanding balance if you default on the loan agreement terms.",
    "annual_fee": "A yearly maintenance fee charged to keep your credit card or credit facility account active.",
    "renewal_fee": "A fee charged when the term of your credit facility or card is extended for another cycle.",
    "gst_tax_references": "Government tax (typically GST at 18%) applied on top of the processing fees, documentation fees, and penalty charges."
}

def get_simple_explanation(canonical_name: str, clause_text: Optional[str]) -> str:
    """
    Attempts to use Ollama/Gemini to simplify the legalese clause.
    Prioritizes local templates to maximize performance and bypass LLM calls.
    """
    name_lower = canonical_name.strip().lower()
    if name_lower in TEMPLATE_EXPLANATIONS:
        return TEMPLATE_EXPLANATIONS[name_lower]
        
    if clause_text and len(clause_text.strip()) > 10:
        try:
            client = OllamaClient()
            if client.check_connection():
                prompt = f"Translate this clause into one plain English sentence:\n'{clause_text}'"
                # Call generate_json or standard text generate (OllamaClient generate_json expects json format)
                res = client.generate_json(
                    prompt=f"Simplify the following text and return a JSON object with a single key 'explanation':\n\"{clause_text}\"",
                    system_prompt=EXPLAINER_SYSTEM_PROMPT
                )
                if isinstance(res, dict) and "explanation" in res:
                    return res["explanation"]
        except Exception:
            pass # fall back to templates
            
    # Fallback to local template matching
    return TEMPLATE_EXPLANATIONS.get(name_lower, "An additional term mentioned in your loan contract.")

def generate_math_example(canonical_name: str, value: Optional[Any], unit: Optional[str], basis: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    Generates a concrete math example based on the charge properties.
    Examples:
      - 4% foreclosure charge -> "On ₹1,00,000 remaining principal, a 4% charge equals ₹4,000"
      - ₹500 late fee -> "If you pay late, you are charged a flat ₹500 penalty"
    """
    name_clean = canonical_name.lower()
    
    if value is None:
        return None
        
    # Safely convert value to float
    val_float = None
    if isinstance(value, (int, float)):
        val_float = float(value)
    else:
        import re
        match = re.search(r'-?\d+(?:\.\d+)?', str(value))
        if match:
            try:
                val_float = float(match.group(0))
            except ValueError:
                pass

    unit_str = str(unit).strip().lower() if unit else ""
    is_percent = "percent" in unit_str or unit_str == "%"
    
    # If we couldn't parse a float value, we can't generate a math calculation
    if val_float is None:
        return {
            "scenario": "Applicable charge",
            "formula": f"Defined terms in contract: {value}",
            "result": "As specified"
        }
        
    if name_clean == "processing_fee":
        if is_percent:
            calc_val = 200000.0 * (val_float / 100.0)
            return {
                "scenario": "Assuming a loan of ₹2,00,000",
                "formula": f"₹2,00,000 x {val_float}%",
                "result": calc_val
            }
        else:
            return {
                "scenario": "Upfront processing fee",
                "formula": f"Fixed charge of ₹{val_float}",
                "result": val_float
            }
            
    elif name_clean in ["foreclosure_charge", "prepayment_charge"]:
        # Usually percentage of outstanding principal
        percent_val = val_float if is_percent else 4.0 # default 4% example if not specified
        calc_val = 10000.0 * (percent_val / 100.0) if percent_val > 100 else 100000.0 * (percent_val / 100.0)
        return {
            "scenario": "Assuming ₹1,00,000 remaining principal" if percent_val <= 100 else "Assuming ₹10,000 remaining principal",
            "formula": f"₹1,00,000 x {percent_val}%" if percent_val <= 100 else f"₹10,000 x {percent_val}%",
            "result": calc_val
        }
        
    elif name_clean == "late_payment_fee":
        if is_percent:
            calc_val = 10000.0 * (val_float / 100.0)
            return {
                "scenario": "On ₹10,000 overdue EMI balance",
                "formula": f"₹10,000 x {val_float}% penalty",
                "result": calc_val
            }
        else:
            return {
                "scenario": "For a missed payment deadline",
                "formula": f"Flat fee of ₹{val_float}",
                "result": val_float
            }
            
    elif name_clean == "bounce_charge":
        return {
            "scenario": "For a failed payment debit/check bounce",
            "formula": f"Flat fee of ₹{val_float} per bounce event",
            "result": val_float
        }
        
    elif name_clean == "documentation_fee":
        return {
            "scenario": "Documentation charges",
            "formula": f"Fixed stamp duty/legal fee of ₹{val_float}",
            "result": val_float
        }
        
    elif name_clean == "insurance":
        return {
            "scenario": "Credit protection insurance premium",
            "formula": f"One-time/recurring charge of ₹{val_float}",
            "result": val_float
        }
        
    # Default fallback
    if is_percent:
        calc_val = 100000.0 * (val_float / 100.0)
        return {
            "scenario": "On an example ₹1,00,000 baseline value",
            "formula": f"₹1,00,000 x {val_float}%",
            "result": calc_val
        }
    else:
        return {
            "scenario": "Applicable charge",
            "formula": f"Fixed fee of ₹{val_float}",
            "result": val_float
        }
