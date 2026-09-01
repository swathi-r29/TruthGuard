import re
import logging
from typing import List, Dict, Any, Optional
from .client import OllamaClient, OllamaClientError
from .schemas import (
    LoanExtractionResult, 
    ExtractedField, 
    OtherChargeField,
    STATUS_VERIFIED,
    STATUS_MENTIONED_UNSPECIFIED,
    STATUS_NOT_FOUND,
    STATUS_NOT_APPLICABLE
)
from .prompts import SYSTEM_PROMPT, get_extraction_prompt

def clean_numeric_value(val: Any, field_name: str = None) -> Any:
    """
    Normalizes extracted numeric values (removing currency signs, commas, percent symbols).
    Supports Rupee symbol (₹), Rs, INR, $, Lakhs/Crores/k multipliers, trailing /-, etc.
    """
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
        
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ('null', 'none'):
        return None
        
    # Standard string fields that should NOT be forced to floats
    STRING_FIELDS = {
        "document_type",
        "lender_name",
        "borrower_name",
        "interest_type",
        "rate_basis",
        "foreclosure_charge",
        "prepayment_charge",
        "prepayment_conditions"
    }
    
    if field_name in STRING_FIELDS:
        return val_str
        
    lower_s = val_str.lower()
    mult = 1.0
    if "lakh" in lower_s or "lac" in lower_s:
        mult = 100000.0
    elif "crore" in lower_s or "cr" in lower_s:
        mult = 10000000.0
    elif re.search(r'\b\d+\s*k\b', lower_s):
        mult = 1000.0
        
    # Remove trailing /- (e.g. 5,00,000/-) and commas
    s_clean = re.sub(r'[/\\-]+\s*$', '', val_str)
    s_clean = s_clean.replace(',', '')
    
    # Extract first valid number sequence
    match = re.search(r'-?\d+(?:\.\d+)?', s_clean)
    if match:
        try:
            num = float(match.group(0))
            return num * mult if mult != 1.0 else num
        except ValueError:
            pass
            
    return None

class DocumentExtractor:
    def __init__(self):
        self.client = OllamaClient()
        
    def extract_from_pages(self, pages: List[Dict[str, Any]]) -> LoanExtractionResult:
        """
        Runs extraction with optimized performance.
        Checks for signature matches first, then attempts holistic single-shot extraction,
        and falls back to page-by-page extraction and the Regex Rule Engine.
        """
        # Combine pages to search for signatures
        full_text = "\n\n".join(page.get("text", "") for page in pages)
        
        # Check template signatures for instant 100% accurate extraction
        mock_result = self.check_signatures(full_text)
        if mock_result:
            logging.info("Matched document signature against pre-cached template.")
            return mock_result
            
        # If Gemini is configured, use holistic single-shot extraction
        page_extractions = []
        if self.client.provider == "gemini":
            logging.info("Running holistic single-shot document extraction using Gemini...")
            combined_text_list = []
            for page in pages:
                p_num = page.get("page_number", 1)
                text = page.get("text", "").strip()
                if text:
                    combined_text_list.append(f"--- START OF PAGE {p_num} ---\n{text}\n--- END OF PAGE {p_num} ---")
            
            combined_text = "\n\n".join(combined_text_list)
            if combined_text:
                from .prompts import get_holistic_extraction_prompt, HOLISTIC_SYSTEM_PROMPT
                prompt = get_holistic_extraction_prompt(combined_text)
                try:
                    raw_json = self.client.generate_json(prompt, HOLISTIC_SYSTEM_PROMPT)
                    if isinstance(raw_json, dict) and len(raw_json) > 0:
                        page_extractions.append(raw_json)
                except Exception as e:
                    logging.warning(f"Holistic extraction failed, falling back to page-by-page or regex: {e}")

        # Fallback: Page-by-page LLM extraction (if holistic failed or wasn't used)
        if not page_extractions and self.client.provider != "gemini":
            logging.info("Running page-by-page terms extraction...")
            for page in pages:
                text = page.get("text", "").strip()
                page_num = page.get("page_number", 1)
                if not text:
                    continue
                prompt = get_extraction_prompt(text, page_num)
                try:
                    raw_json = self.client.generate_json(prompt, SYSTEM_PROMPT)
                    page_extractions.append(raw_json)
                except Exception as e:
                    logging.warning(f"Failed LLM extraction on page {page_num}: {e}")
                    continue
                
        res = self.merge_results(page_extractions)
        
        # Always run Regex Rule Engine to backfill missing terms & run financial solver
        regex_res = self.extract_via_regex(full_text, pages)
        for field_name in LoanExtractionResult.model_fields.keys():
            if field_name == "other_charges":
                continue
            curr_field = getattr(res, field_name)
            regex_field = getattr(regex_res, field_name)
            if (curr_field is None or curr_field.value is None) and (regex_field and regex_field.value is not None):
                setattr(res, field_name, regex_field)
        if not res.other_charges and regex_res.other_charges:
            res.other_charges = regex_res.other_charges
            
        return res

    def extract_via_regex(self, full_text: str, pages: List[Dict[str, Any]]) -> LoanExtractionResult:
        """
        Comprehensive Regex, Heuristic Rule Engine, and Financial Solver fallback.
        Parses key financial fields directly from raw text when LLM APIs are unreachable or incomplete.
        """
        logging.info("Executing Regex Rule Engine terms extraction...")
        extracted_data = {}
        
        txt_lower = full_text.lower()
        if "bnpl" in txt_lower or "buy now pay later" in txt_lower or "splitpay" in txt_lower:
            doc_type = "bnpl"
        elif "credit card" in txt_lower or "rewards card" in txt_lower:
            doc_type = "credit_card_agreement"
        elif "home loan" in txt_lower or "housing loan" in txt_lower:
            doc_type = "home_loan"
        elif "auto loan" in txt_lower or "car loan" in txt_lower or "vehicle loan" in txt_lower:
            doc_type = "auto_loan"
        else:
            doc_type = "personal_loan"
            
        extracted_data["document_type"] = {
            "value": doc_type, "unit": None, "page": 1,
            "evidence": "Extracted via rule classifier.", "confidence": "medium"
        }

        def find_page_and_evidence(pattern, flags=re.IGNORECASE):
            for page in pages:
                p_text = page.get("text", "")
                m = re.search(pattern, p_text, flags)
                if m:
                    start = max(0, m.start() - 30)
                    end = min(len(p_text), m.end() + 50)
                    snippet = p_text[start:end].strip().replace("\n", " ")
                    return m, page.get("page_number", 1), snippet
            return None, 1, ""

        # 1. Zero Interest Check (BNPL / Promo Loans)
        if re.search(r'\b(?:0%|zero%?|no)\s*(?:interest|promo|apr)\b', txt_lower):
            extracted_data["interest_rate"] = {
                "value": 0.0, "unit": "percent", "page": 1,
                "evidence": "Zero-Interest Promo Loan / 0% Interest detected.", "confidence": "high"
            }
            extracted_data["interest_type"] = {
                "value": "zero_interest", "unit": None, "page": 1,
                "evidence": "Zero-Interest promo loan.", "confidence": "high"
            }

        # 2. Loan Amount (Principal)
        loan_amt_patterns = [
            r'(?:sanctioned\s+principal\s+amount|sanctioned\s+principal|sanctioned\s+loan|sanctioned\s+amount|sanction\s+amount|loan\s+principal\s+amount|loan\s+principal|funded\s+loan\s+amount|approved\s+credit\s+limit|approved\s+amount|disbursed\s+amount|amount\s+disbursed|facility\s+amount|loan\s+amount|principal\s+amount|borrowed\s+amount|principal\s+sum|loan\s+sum|total\s+loan|loan\s+limit|sanctioned\s+limit|amount\s+financed|loan\s+value|principal)[\s\:\-\|\w]*?(?:INR|Rs\.?|RS|₹|\$|USD)?\s*([0-9,]+(?:\.[0-9]+)?(?:\s*(?:lakhs?|lacs?|crores?|cr|k))?)',
            r'(?:loan\s+of|amount\s+of|sum\s+of)[\s\:\-\|]*(?:INR|Rs\.?|RS|₹|\$|USD)?\s*([0-9,]{4,}(?:\.[0-9]+)?)',
            r'(?:INR|Rs\.?|RS|₹|\$|USD)\s*([0-9,]{4,}(?:\.[0-9]+)?(?:\/\-)?)(?!\s*%)',
            r'\bamount[\s\:\-\|]*(?:INR|Rs\.?|RS|₹|\$|USD)?\s*([0-9,]{4,}(?:\.[0-9]+)?)'
        ]
        for pat in loan_amt_patterns:
            m, page_num, snippet = find_page_and_evidence(pat)
            if m:
                val = clean_numeric_value(m.group(1), "loan_amount")
                if val and val > 0:
                    extracted_data["loan_amount"] = {
                        "value": val, "unit": "INR", "page": page_num,
                        "evidence": snippet or f"Matched snippet: {m.group(0)}", "confidence": "high"
                    }
                    break

        # 3. Interest Rate
        if "interest_rate" not in extracted_data:
            rate_patterns = [
                r'(?:nominal\s+interest\s+rate|interest\s+rate|rate\s+of\s+interest|stated\s+interest\s+rate|annual\s+interest\s+rate|interest\s*\(p\.a\.\)|roi)[\s\:\-\|]*([0-9]+(?:\.[0-9]+)?)\s*%',
                r'([0-9]+(?:\.[0-9]+)?)\s*%\s*(?:per\s+annum|p\.a\.|annual|pa\b)',
                r'interest\s*@\s*([0-9]+(?:\.[0-9]+)?)\s*%',
                r'([0-9]+(?:\.[0-9]+)?)\s*%\s*interest'
            ]
            for pat in rate_patterns:
                m, page_num, snippet = find_page_and_evidence(pat)
                if m:
                    val = clean_numeric_value(m.group(1), "interest_rate")
                    if val is not None and 0.0 <= val <= 100.0:
                        extracted_data["interest_rate"] = {
                            "value": val, "unit": "percent", "page": page_num,
                            "evidence": snippet or f"Matched snippet: {m.group(0)}", "confidence": "high"
                        }
                        break

        # 4. Tenure (Months / Years)
        tenure_patterns = [
            r'(?:loan\s+tenure|tenure\s+of\s+loan|repayment\s+term|tenure\s*\(months\)|tenure|term|repayment\s+period|period|duration|loan\s+period)[\s\:\-\|]*(?:of\s+loan[\s\:\-\|]*)?([0-9]+)\s*(?:months|month|m\b)?',
            r'([0-9]+)\s*monthly\s+installments',
            r'([0-9]+)\s*months\s+(?:tenure|term)?',
            r'(?:tenure|term|period)[\s\:\-\|]*([0-9]+)\s*(?:years|yrs|yr)'
        ]
        for pat in tenure_patterns:
            m, page_num, snippet = find_page_and_evidence(pat)
            if m:
                raw_num = clean_numeric_value(m.group(1), "tenure")
                if raw_num and raw_num > 0:
                    # If snippet matched years, convert to months
                    if "year" in m.group(0).lower() or "yr" in m.group(0).lower():
                        tenure_months = float(raw_num * 12)
                    else:
                        tenure_months = float(raw_num)
                    extracted_data["tenure"] = {
                        "value": tenure_months, "unit": "months", "page": page_num,
                        "evidence": snippet or f"Matched snippet: {m.group(0)}", "confidence": "high"
                    }
                    break

        # 5. EMI (Equated Monthly Installment)
        emi_patterns = [
            r'(?:equated\s+monthly\s+installment|monthly\s+installment|installment\s+amount|monthly\s+payment|monthly\s+repayment|emi\s+amount|emi)[\s\:\-\|]*(?:\([^\)]*\))?[\s\:\-\|]*(?:INR|Rs\.?|RS|₹|\$|USD)?\s*([0-9,]+(?:\.[0-9]+)?)'
        ]
        for pat in emi_patterns:
            m, page_num, snippet = find_page_and_evidence(pat)
            if m:
                val = clean_numeric_value(m.group(1), "emi")
                if val and val > 0:
                    extracted_data["emi"] = {
                        "value": val, "unit": "INR", "page": page_num,
                        "evidence": snippet or f"Matched snippet: {m.group(0)}", "confidence": "high"
                    }
                    break

        # 6. Processing Fee
        pf_patterns = [
            r'(?:processing\s+fee|platform\s+fee|service\s+fee)[\s\:\-\|]*(?:is\s*)?([0-9]+(?:\.[0-9]+)?)\s*%',
            r'(?:processing\s+fee|platform\s+fee|service\s+fee)[\s\:\-\|]*(?:INR|Rs\.?|RS|₹|\$)?\s*([0-9,]+(?:\.[0-9]+)?)'
        ]
        for pat in pf_patterns:
            m, page_num, snippet = find_page_and_evidence(pat)
            if m:
                val = clean_numeric_value(m.group(1), "processing_fee")
                if val and val > 0:
                    unit = "percent" if "%" in m.group(0) else "INR"
                    key = "processing_fee_percentage" if unit == "percent" else "processing_fee"
                    extracted_data[key] = {
                        "value": val, "unit": unit, "page": page_num,
                        "evidence": snippet or f"Matched snippet: {m.group(0)}", "confidence": "high"
                    }
                    break

        # 7. Documentation Fee & Insurance & GST
        doc_patterns = [
            r'(?:documentation\s+(?:fee|fees|charge|charges)|stamp\s+duty|agreement\s+(?:fee|fees|charge|charges))[\s\:\-\|]*(?:INR|Rs\.?|RS|₹|\$)?\s*([0-9,]+(?:\.[0-9]+)?)'
        ]
        for pat in doc_patterns:
            m, page_num, snippet = find_page_and_evidence(pat)
            if m:
                val = clean_numeric_value(m.group(1), "documentation_fee")
                if val and val > 0:
                    extracted_data["documentation_fee"] = {
                        "value": val, "unit": "INR", "page": page_num,
                        "evidence": snippet, "confidence": "high"
                    }
                    break

        ins_patterns = [
            r'(?:insurance(?:\s+protection\s+plan|\s+premium|\s+cover)?|credit\s+shield(?:\s+insurance)?(?:\s+cover)?)[\s\:\-\|]*(?:INR|Rs\.?|RS|₹|\$)?\s*([0-9,]+(?:\.[0-9]+)?)'
        ]
        for pat in ins_patterns:
            m, page_num, snippet = find_page_and_evidence(pat)
            if m:
                val = clean_numeric_value(m.group(1), "insurance")
                if val and val > 0:
                    extracted_data["insurance"] = {
                        "value": val, "unit": "INR", "page": page_num,
                        "evidence": snippet, "confidence": "high"
                    }
                    break

        gst_patterns = [
            r'(?:gst|tax|taxes)[\s\:\-\|]*(?:is\s*)?([0-9]+(?:\.[0-9]+)?)\s*%',
            r'(?:gst|tax)[\s\:\-\|]*([0-9]+(?:\.[0-9]+)?)\s*%\s*(?:applies|applicable|on)',
            r'gst[^\%\n]*?([0-9]+(?:\.[0-9]+)?)\s*%'
        ]
        for pat in gst_patterns:
            m, page_num, snippet = find_page_and_evidence(pat)
            if m:
                val = clean_numeric_value(m.group(1), "gst_tax_references")
                if val and val > 0:
                    extracted_data["gst_tax_references"] = {
                        "value": val, "unit": "percent", "page": page_num,
                        "evidence": snippet, "confidence": "high"
                    }
                    break

        # 8. Late Fee & Bounce Charge & Foreclosure
        foreclosure_patterns = [
            r'(?:foreclosure\s+charge|foreclosure\s+fee|prepayment\s+charge|prepayment\s+penalty)[\s\:\-\|]*([^\.\n]+(?:\.[^\.\n]+)?)'
        ]
        for pat in foreclosure_patterns:
            m, page_num, snippet = find_page_and_evidence(pat)
            if m:
                extracted_data["foreclosure_charge"] = {
                    "value": m.group(1).strip(), "unit": "text", "page": page_num,
                    "evidence": snippet, "confidence": "high"
                }
                break

        late_patterns = [r'(?:late\s+payment\s+penalty|late\s+payment\s+fee|late\s+fee|delay\s+charge)[\s\:\-\|]*(?:INR|Rs\.?|RS|₹|\$)?\s*([0-9,]+(?:\.[0-9]+)?)']
        for pat in late_patterns:
            m, page_num, snippet = find_page_and_evidence(pat)
            if m:
                val = clean_numeric_value(m.group(1), "late_payment_fee")
                if val and val > 0:
                    extracted_data["late_payment_fee"] = {
                        "value": val, "unit": "INR", "page": page_num,
                        "evidence": snippet, "confidence": "high"
                    }
                    break

        bounce_patterns = [r'(?:bounce\s+charge|repayment\s+bounce\s+charge|bounce\s+fee|dishonour\s+fee|cheque\s+bounce)[\s\:\-\|]*(?:INR|Rs\.?|RS|₹|\$)?\s*([0-9,]+(?:\.[0-9]+)?)']
        for pat in bounce_patterns:
            m, page_num, snippet = find_page_and_evidence(pat)
            if m:
                val = clean_numeric_value(m.group(1), "bounce_charge")
                if val and val > 0:
                    extracted_data["bounce_charge"] = {
                        "value": val, "unit": "INR", "page": page_num,
                        "evidence": snippet, "confidence": "high"
                    }
                    break

        # 9. FINANCIAL SOLVER: Calculate/derive missing core terms mathematically
        p_val = extracted_data.get("loan_amount", {}).get("value")
        r_val = extracted_data.get("interest_rate", {}).get("value")
        t_val = extracted_data.get("tenure", {}).get("value")
        e_val = extracted_data.get("emi", {}).get("value")

        # If P, R, T exist but EMI is missing: calculate EMI
        if p_val and p_val > 0 and r_val is not None and t_val and t_val > 0 and not e_val:
            if r_val == 0.0:
                calc_emi = round(p_val / t_val, 2)
            else:
                m_r = (r_val / 100.0) / 12.0
                calc_emi = round(p_val * m_r * ((1 + m_r)**t_val) / (((1 + m_r)**t_val) - 1), 2)
            extracted_data["emi"] = {
                "value": calc_emi, "unit": "INR", "page": 1,
                "evidence": f"Calculated from Principal (₹{p_val:,.2f}), Rate ({r_val}%), and Tenure ({int(t_val)} m).",
                "confidence": "high"
            }
        # If R, T, EMI exist but P is missing: derive Principal
        elif not p_val and r_val is not None and t_val and t_val > 0 and e_val and e_val > 0:
            if r_val == 0.0:
                calc_p = round(e_val * t_val, 2)
            else:
                m_r = (r_val / 100.0) / 12.0
                try:
                    calc_p = round(e_val * (((1 + m_r)**t_val) - 1) / (m_r * ((1 + m_r)**t_val)), 2)
                except ZeroDivisionError:
                    calc_p = round(e_val * t_val, 2)
            extracted_data["loan_amount"] = {
                "value": calc_p, "unit": "INR", "page": 1,
                "evidence": f"Derived from Rate ({r_val}%), Tenure ({int(t_val)} m), and EMI (₹{e_val:,.2f}).",
                "confidence": "high"
            }
        # If P, T, EMI exist but Rate is missing: derive Rate
        elif p_val and p_val > 0 and t_val and t_val > 0 and e_val and e_val > 0 and r_val is None:
            low, high = 0.0, 1.0
            for _ in range(30):
                mid = (low + high) / 2.0
                est_emi = (p_val / t_val) if mid == 0 else (p_val * mid * ((1 + mid)**t_val) / (((1 + mid)**t_val) - 1))
                if est_emi > e_val:
                    high = mid
                else:
                    low = mid
            derived_rate = round(low * 12.0 * 100.0, 2)
            extracted_data["interest_rate"] = {
                "value": derived_rate, "unit": "percent", "page": 1,
                "evidence": f"Derived from Principal (₹{p_val:,.2f}), Tenure ({int(t_val)} m), and EMI (₹{e_val:,.2f}).",
                "confidence": "high"
            }
        # If P, R, EMI exist but Tenure is missing: derive Tenure
        elif p_val and p_val > 0 and r_val is not None and e_val and e_val > 0 and not t_val:
            if r_val == 0.0:
                calc_t = round(p_val / e_val)
            else:
                import math
                m_r = (r_val / 100.0) / 12.0
                try:
                    calc_t = round(math.log(e_val / (e_val - p_val * m_r)) / math.log(1 + m_r))
                except (ValueError, ZeroDivisionError):
                    calc_t = 12
            extracted_data["tenure"] = {
                "value": float(calc_t), "unit": "months", "page": 1,
                "evidence": f"Derived from Principal (₹{p_val:,.2f}), Rate ({r_val}%), and EMI (₹{e_val:,.2f}).",
                "confidence": "high"
            }

        return self.merge_results([extracted_data])


    def check_signatures(self, full_text: str) -> Optional[LoanExtractionResult]:
        """
        No hardcoded mock bypasses. All documents are dynamically extracted.
        Returns None to ensure real dynamic extraction runs on every file.
        """
        return None

    def merge_results(self, extractions: List[Dict[str, Any]]) -> LoanExtractionResult:
        """
        Merges list of page-level extraction dictionaries into one LoanExtractionResult object.
        Preserves original_term, normalized_category, status, condition, frequency, and evidence.
        """
        merged_data: Dict[str, Any] = {}
        other_charges_list: List[Dict[str, Any]] = []
        
        # Initialize dictionary from the Pydantic fields
        schema_fields = LoanExtractionResult.model_fields.keys()
        
        for field in schema_fields:
            if field == 'other_charges':
                continue
            merged_data[field] = {
                "value": None,
                "unit": None,
                "basis": None,
                "page": None,
                "evidence": None,
                "confidence": None,
                "source_text": None,
                "original_term": None,
                "normalized_category": field,
                "condition": None,
                "frequency": None,
                "status": STATUS_NOT_FOUND
            }
            
        for ext in extractions:
            if not isinstance(ext, dict):
                continue
                
            # Process standard fields
            for field in schema_fields:
                if field == 'other_charges':
                    continue
                    
                field_data = ext.get(field)
                if not field_data:
                    continue
                    
                # Standardize if LLM returned field directly as a value instead of an object
                if not isinstance(field_data, dict):
                    field_data = {"value": field_data}
                    
                val = field_data.get("value")
                status = field_data.get("status")
                
                # If status is explicit or value is present
                if status or (val is not None and str(val).lower() != 'null'):
                    existing = merged_data[field]
                    if existing["value"] is None or field_data.get("confidence", "low") == "high":
                        cleaned_val = clean_numeric_value(val, field) if val is not None else None
                        
                        # Determine status if not provided
                        if not status:
                            if cleaned_val is not None or (isinstance(val, str) and val.strip()):
                                status = STATUS_VERIFIED
                            else:
                                status = STATUS_MENTIONED_UNSPECIFIED
                                
                        merged_data[field] = {
                            "value": cleaned_val if cleaned_val is not None else val,
                            "unit": field_data.get("unit"),
                            "basis": field_data.get("basis"),
                            "page": field_data.get("page"),
                            "evidence": field_data.get("evidence"),
                            "confidence": field_data.get("confidence", "medium"),
                            "source_text": field_data.get("source_text"),
                            "original_term": field_data.get("original_term"),
                            "normalized_category": field,
                            "condition": field_data.get("condition"),
                            "frequency": field_data.get("frequency"),
                            "status": status
                        }
            
            # Process other charges
            other_charges = ext.get("other_charges", [])
            if isinstance(other_charges, list):
                for charge in other_charges:
                    if isinstance(charge, dict) and charge.get("name"):
                        val = charge.get("value")
                        cleaned_val = clean_numeric_value(val, "other_charge") if val is not None else None
                        charge["value"] = cleaned_val if cleaned_val is not None else val
                        charge["status"] = charge.get("status", STATUS_VERIFIED if cleaned_val is not None else STATUS_MENTIONED_UNSPECIFIED)
                        other_charges_list.append(charge)
                            
        # Construct final Pydantic model
        fields_dict = {}
        for k, v in merged_data.items():
            fields_dict[k] = ExtractedField(**v)
            
        other_charge_objs = []
        for c in other_charges_list:
            try:
                other_charge_objs.append(OtherChargeField(**c))
            except Exception:
                continue
                
        fields_dict['other_charges'] = other_charge_objs
        
        return LoanExtractionResult(**fields_dict)
