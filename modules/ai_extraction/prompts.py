import json
from .schemas import LoanExtractionResult

SYSTEM_PROMPT = """You are a precise financial document analysis AI. Your task is to extract loan terms, interest rates, fees, and clauses from the provided document page.

CRITICAL INSTRUCTIONS:
1. ONLY extract information that is explicitly stated in the text. 
2. If a specific field is not mentioned or not found in the text, you MUST set its 'value' to null. Do not invent, assume, or guess any value.
3. For every extracted field, you must provide:
   - 'value': the extracted number (float/int) or string (e.g. name, type). Set to null if not found.
   - 'unit': the unit (e.g. 'percent', 'INR', 'months', 'days', or null).
   - 'basis': how the fee is calculated (e.g. 'principal', 'outstanding_principal', 'flat', or null).
   - 'page': the page number provided in the prompt.
   - 'evidence': the exact, verbatim quote or sentence from the text containing the value.
   - 'confidence': your confidence rating ('high', 'medium', 'low').
   - 'source_text': verbatim surrounding context.
4. Output your response as a single, valid JSON object matching the requested schema. Do not output any conversational text, markdown formatting blocks (like ```json), or notes. Only output the raw JSON.
5. NUMERIC FIELDS FORMATTING: For all fields that represent numeric values (e.g., loan_amount, interest_rate, tenure, emi, processing_fee, insurance, documentation_fee, gst_tax_references, late_payment_fee, bounce_charge, annual_fee, renewal_fee, lock_in_period), the 'value' field MUST be a clean numeric float or integer (or null). Do NOT include currency symbols (like ₹, $, Rs), commas, percent signs (%), or words (like "months", "years"). For example:
   - "Sanctioned loan of Rs. 2,00,000" -> value: 200000.0, unit: "INR"
   - "Stated Interest Rate: 18.0% per annum" -> value: 18.0, unit: "percent", basis: "annual"
   - "Tenure: 24 Months" -> value: 24.0, unit: "months"
   - "Processing Fee: 2% of loan principal" -> value: 2.0, unit: "percent", basis: "principal"
   - "Late Payment Fee: Rs. 500 flat penalty" -> value: 500.0, unit: "INR", basis: "flat"
"""

def get_extraction_prompt(page_text: str, page_number: int) -> str:
    # Generate JSON schema structure to guide the model
    schema_hint = LoanExtractionResult.model_json_schema()
    
    prompt = f"""DOCUMENT PAGE TEXT (Page {page_number}):
---
{page_text}
---

Extract the financial terms from the above text. Return a JSON object matching this schema structure:
{json.dumps(schema_hint, indent=2)}

Remember:
- If a charge/term is not in the text, set value to null.
- Provide the exact verbatim snippet as 'evidence'.
- The current page number is {page_number}. Set 'page': {page_number} for any field you extract from this text.
"""
    return prompt

HOLISTIC_SYSTEM_PROMPT = """You are a precise financial document analysis AI. Your task is to extract loan terms, interest rates, fees, and clauses from the provided full document text.

CRITICAL INSTRUCTIONS:
1. ONLY extract information that is explicitly stated in the text. 
2. If a specific field is not mentioned or not found in the text, you MUST set its 'value' to null. Do not invent, assume, or guess any value.
3. For every extracted field, you must provide:
   - 'value': the extracted number (float/int) or string (e.g. name, type). Set to null if not found.
   - 'unit': the unit (e.g. 'percent', 'INR', 'months', 'days', or null).
   - 'basis': how the fee is calculated (e.g. 'principal', 'outstanding_principal', 'flat', or null).
   - 'page': the page number (1-based index) where the evidence was found.
   - 'evidence': the exact, verbatim quote or sentence from the text containing the value.
   - 'confidence': your confidence rating ('high', 'medium', 'low').
   - 'source_text': verbatim surrounding context.
4. Output your response as a single, valid JSON object matching the requested schema. Do not output any conversational text, markdown formatting blocks (like ```json), or notes. Only output the raw JSON.
5. NUMERIC FIELDS FORMATTING: For all fields that represent numeric values (e.g., loan_amount, interest_rate, tenure, emi, processing_fee, insurance, documentation_fee, gst_tax_references, late_payment_fee, bounce_charge, annual_fee, renewal_fee, lock_in_period), the 'value' field MUST be a clean numeric float or integer (or null). Do NOT include currency symbols (like ₹, $, Rs), commas, percent signs (%), or words (like "months", "years").
6. PAGE RESOLUTION: The document contains text from multiple pages, marked by indicators like '--- PAGE N ---'. You MUST determine the correct 1-based page number where the evidence is found and set the 'page' field accordingly.
"""

def get_holistic_extraction_prompt(combined_pages_text: str) -> str:
    schema_hint = LoanExtractionResult.model_json_schema()
    
    prompt = f"""DOCUMENT COMBINED TEXT:
---
{combined_pages_text}
---

Extract the financial terms from the above text. Return a JSON object matching this schema structure:
{json.dumps(schema_hint, indent=2)}

Remember:
- If a charge/term is not in the text, set value to null.
- Provide the exact verbatim snippet as 'evidence'.
- Map each finding to its correct 'page' number based on the page markers.
"""
    return prompt
