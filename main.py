import os
import shutil
import logging
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import config
from modules.document_processor import process_document
from modules.ai_extraction import DocumentExtractor
from modules.charge_detection import detect_charges
from modules.financial_engine import calculate_real_cost_metrics
from modules.analyzer import calculate_transparency_score, calculate_effective_rates, check_regulatory_compliance
from modules.explanation.explainer import get_simple_explanation, generate_math_example
from modules.debt_strategy.payoff_simulator import simulate_loan_payoff
from modules.debt_strategy.ranking import rank_debts, get_strategy_explanation

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("debt-detox-backend")

app = FastAPI(
    title="Debt Detox — API",
    description="Backend API for AI-powered loan agreement and debt analysis.",
    version="1.0"
)

# Enable CORS for React local dev server (default port 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- PYDANTIC SCHEMAS ---

class ChargeItem(BaseModel):
    canonical_name: str
    original_name: str
    value: Optional[float] = None
    unit: str
    basis: str
    page: Optional[int] = 1
    evidence: Optional[str] = ""
    classification: str
    is_mandatory: bool
    is_conditional: bool

class ManualCalculateInput(BaseModel):
    principal: float
    interest_rate_annual: float
    tenure_months: int
    interest_type: str = "reducing_balance"
    emi: Optional[float] = None
    charges: List[ChargeItem] = []

class SimulationInput(BaseModel):
    balance: float
    rate_annual: float
    current_emi: float
    extra_monthly: float
    one_time_payment: float = 0.0
    one_time_month: int = 1

class DebtItem(BaseModel):
    name: str
    balance: float
    interest_rate: float
    emi: float

class StrategyInput(BaseModel):
    debts: List[DebtItem]
    strategy: str = "avalanche"

class ChatInput(BaseModel):
    message: str
    context_text: str
    history: List[Dict[str, str]] = []

# --- HELPER COMPILERS ---

def compile_analysis_payload(
    doc_name: str,
    doc_type: str,
    total_pages: int,
    ocr_used: bool,
    extracted_obj: Any,
    charges_list: List[Dict[str, Any]],
    metrics: Dict[str, Any],
    effective_rates: Dict[str, Any],
    transparency: Dict[str, Any],
    document_text: str = ""
) -> Dict[str, Any]:
    """Compiles metrics, charges, explanations, and math examples into a unified UI payload."""
    
    # Standardize charges into frontend-friendly lists
    # Generate explanations & math examples for charges
    explanations = {}
    math_examples = {}
    
    for c in charges_list:
        canonical_name = c["canonical_name"]
        evidence = c.get("evidence", "")
        val = c.get("value")
        unit = c.get("unit", "currency")
        basis = c.get("basis", "flat")
        
        # Plain English simplification
        explanations[canonical_name] = get_simple_explanation(canonical_name, evidence)
        
        # Concrete Math Example
        if val is not None:
            math_examples[canonical_name] = generate_math_example(canonical_name, val, unit, basis)
            
    # Calculate overall confidence
    conf_values = []
    schema_fields = list(extracted_obj.model_fields.keys()) if hasattr(extracted_obj, "model_fields") else []
    for field_name in schema_fields:
        if field_name == "other_charges":
            continue
        field_data = getattr(extracted_obj, field_name, None)
        if field_data and field_data.value is not None and str(field_data.value).lower() != 'null':
            conf = field_data.confidence or "medium"
            conf_values.append(0.95 if conf == "high" else (0.80 if conf == "medium" else 0.50))
            
    # Handle dictionary representation (fallback/mock)
    if not schema_fields and isinstance(extracted_obj, dict):
        for k, v in extracted_obj.items():
            if k == "other_charges":
                continue
            if isinstance(v, dict) and v.get("value") is not None:
                conf = v.get("confidence", "medium")
                conf_values.append(0.95 if conf == "high" else (0.80 if conf == "medium" else 0.50))
                
    overall_conf_pct = int(sum(conf_values) / len(conf_values) * 100) if conf_values else 85
    
    # Determine audit status
    principal = metrics.get("loan_amount", 0.0) if metrics else 0.0
    rate = metrics.get("interest_rate_annual") if metrics else None
    tenure = metrics.get("tenure_months", 0) if metrics else 0
    
    has_principal = (principal > 0.0)
    has_rate = (rate is not None and rate >= 0.0)
    has_tenure = (tenure > 0)
    
    if not has_principal and not has_rate and not has_tenure:
        audit_status = "FAILED"
        data_source_badge = "DATA SOURCE: EXTRACTION FAILED"
        calc_source_badge = "CALCULATION UNAVAILABLE — REQUIRED CONTRACT INFORMATION IS MISSING"
    elif not has_principal or not has_rate or not has_tenure:
        audit_status = "PARTIAL"
        data_source_badge = "DATA SOURCE: CURRENT UPLOADED DOCUMENT (PARTIAL)"
        calc_source_badge = "CALCULATION SOURCE: PARTIAL CONTRACT DATA"
    else:
        audit_status = "VERIFIED"
        data_source_badge = "DATA SOURCE: CURRENT UPLOADED DOCUMENT"
        calc_source_badge = "CALCULATION SOURCE: VERIFIED CONTRACT DATA"
        
    # Build dictionary of all extracted terms with status & page evidence
    terms_map = {}
    schema_fields = list(extracted_obj.model_fields.keys()) if hasattr(extracted_obj, "model_fields") else []
    for field_name in schema_fields:
        if field_name == "other_charges":
            continue
        field_data = getattr(extracted_obj, field_name, None)
        if field_data:
            terms_map[field_name] = {
                "original_term": getattr(field_data, "original_term", None) or field_name.replace("_", " ").title(),
                "normalized_category": field_name,
                "value": field_data.value,
                "unit": field_data.unit,
                "basis": field_data.basis,
                "page": field_data.page or 1,
                "evidence": field_data.evidence or "",
                "confidence": field_data.confidence or "medium",
                "status": getattr(field_data, "status", "VERIFIED" if field_data.value is not None else "NOT FOUND")
            }
            
    # Ensure real_apr is set on metrics for compliance checking
    if metrics and "real_apr" not in metrics and effective_rates:
        metrics["real_apr"] = effective_rates.get("effective_annual_cost_rate", metrics.get("interest_rate_annual", 0.0))
        
    compliance_alerts = check_regulatory_compliance(metrics or {}, charges_list)
        
    return {
        "success": True,
        "doc_name": doc_name,
        "doc_type": doc_type,
        "total_pages": total_pages,
        "ocr_used": ocr_used,
        "audit_status": audit_status,
        "data_source_badge": data_source_badge,
        "calc_source_badge": calc_source_badge,
        "overall_confidence": overall_conf_pct,
        "terms": terms_map,
        "metrics": metrics,
        "effective_rates": effective_rates,
        "transparency": transparency,
        "charges": charges_list,
        "explanations": explanations,
        "math_examples": math_examples,
        "compliance_alerts": compliance_alerts,
        "document_text": document_text
    }

# --- ROUTES ---

@app.get("/api/health")
def health_check():
    try:
        extractor = DocumentExtractor()
        llm_ok = extractor.client.check_connection()
        model_name = extractor.client.model
    except Exception as e:
        logger.error(f"Health check failed to initialize client: {e}")
        llm_ok = False
        model_name = "unknown"
        
    return {
        "status": "ok",
        "llm_provider": config.LLM_PROVIDER,
        "llm_model": model_name,
        "llm_connected": llm_ok
    }

@app.post("/api/analyze")
async def analyze_document(file: UploadFile = File(...)):
    try:
        logger.info(f"Received file for analysis: {file.filename}")
        
        # Check if this matches a preloaded sample document name
        sample_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_documents")
        if file.filename in os.listdir(sample_dir):
            logger.info(f"Loading preloaded sample document from server path: {file.filename}")
            sample_path = os.path.join(sample_dir, file.filename)
            with open(sample_path, "rb") as sf:
                file_bytes = sf.read()
        else:
            # Read file bytes
            file_bytes = await file.read()
            
        # Save file locally inside uploads/ directory
        upload_path = config.UPLOADS_DIR / file.filename
        with open(upload_path, "wb") as f:
            f.write(file_bytes)
            
        # 1. Process Document (pyMuPDF / OCR)
        doc_result = process_document(file_bytes, file.filename)
        if not doc_result.get("success"):
            return {
                "success": False,
                "error": f"Failed to process document pages: {doc_result.get('error')}",
                "audit_status": "FAILED"
            }
            
        pages = doc_result["pages"]
        total_pages = doc_result["total_pages"]
        ocr_used = doc_result["ocr_used"]
        file_type = doc_result.get("file_type", "pdf")
        full_text = doc_result.get("full_text", "")
        
        # 2. Extract Terms (with holistic + signature bypass support)
        extractor = DocumentExtractor()
        extracted = extractor.extract_from_pages(pages)
        
        # 3. Detect Charges
        charges = detect_charges(extracted, pages)
        
        # 4. Financial Calculations
        principal = extracted.loan_amount.value or 0.0
        rate = extracted.interest_rate.value or 0.0
        tenure = int(extracted.tenure.value) if extracted.tenure.value else 0
        emi = extracted.emi.value or 0.0
        interest_type = extracted.interest_type.value or "reducing_balance"
        
        metrics = calculate_real_cost_metrics(
            principal=principal,
            interest_rate_annual=rate,
            tenure_months=tenure,
            charges=charges,
            interest_type=interest_type,
            override_emi=emi if emi > 0 else None,
            tax_rate_percent=18.0  # Default standard tax
        )
        
        # 5. Effective Rates
        effective_rates = calculate_effective_rates(
            net_disbursed=metrics["net_disbursed_amount"],
            emi=metrics["emi"],
            tenure_months=metrics["tenure_months"]
        )
        
        # 6. Transparency Score
        transparency = calculate_transparency_score(metrics, charges, total_pages)
        
        # Compile response
        payload = compile_analysis_payload(
            doc_name=file.filename,
            doc_type=file_type,
            total_pages=total_pages,
            ocr_used=ocr_used,
            extracted_obj=extracted,
            charges_list=charges,
            metrics=metrics,
            effective_rates=effective_rates,
            transparency=transparency,
            document_text=full_text
        )
        return payload
        
    except Exception as e:
        logger.error(f"Unexpected error in /api/analyze: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"An unexpected error occurred during AI analysis: {str(e)}",
            "audit_status": "FAILED"
        }

@app.post("/api/calculate")
def calculate_manual_overrides(inputs: ManualCalculateInput):
    try:
        # Convert Pydantic Charges to standard Dict lists
        charges_list = []
        for c in inputs.charges:
            charges_list.append(c.model_dump())
            
        # Run calculations
        metrics = calculate_real_cost_metrics(
            principal=inputs.principal,
            interest_rate_annual=inputs.interest_rate_annual,
            tenure_months=inputs.tenure_months,
            charges=charges_list,
            interest_type=inputs.interest_type,
            override_emi=inputs.emi if inputs.emi and inputs.emi > 0 else None,
            tax_rate_percent=18.0
        )
        
        # Effective rates
        effective_rates = calculate_effective_rates(
            net_disbursed=metrics["net_disbursed_amount"],
            emi=metrics["emi"],
            tenure_months=metrics["tenure_months"]
        )
        
        # Transparency score
        transparency = calculate_transparency_score(metrics, charges_list, 1)
        
        # Compile payload
        # Mock extracted representation to satisfy overall confidence builder
        mock_extracted = {
            "loan_amount": {"value": inputs.principal},
            "interest_rate": {"value": inputs.interest_rate_annual},
            "tenure": {"value": inputs.tenure_months}
        }
        
        payload = compile_analysis_payload(
            doc_name="Manual Entry Mode",
            doc_type="pdf",
            total_pages=1,
            ocr_used=False,
            extracted_obj=mock_extracted,
            charges_list=charges_list,
            metrics=metrics,
            effective_rates=effective_rates,
            transparency=transparency
        )
        return payload
        
    except Exception as e:
        logger.error(f"Error in manual /api/calculate: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/simulate")
def run_simulation(inputs: SimulationInput):
    try:
        sim_result = simulate_loan_payoff(
            balance=inputs.balance,
            rate_annual=inputs.rate_annual,
            current_emi=inputs.current_emi,
            extra_monthly=inputs.extra_monthly,
            one_time_payment=inputs.one_time_payment,
            one_time_month=inputs.one_time_month
        )
        return sim_result
    except Exception as e:
        logger.error(f"Error in simulation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/strategy")
def compare_debts(inputs: StrategyInput):
    try:
        # Convert input debts to dicts
        debts_dict = [d.model_dump() for d in inputs.debts]
        ranked = rank_debts(debts_dict, inputs.strategy)
        explanation = get_strategy_explanation(inputs.strategy)
        
        return {
            "debts": ranked,
            "explanation": explanation
        }
    except Exception as e:
        logger.error(f"Error in ranking strategies: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
def chat_with_loan(inputs: ChatInput):
    REFUSAL_MSG = "This information is not available in the uploaded document"

    ctx = inputs.context_text or ""
    if "No active document analyzed" in ctx or not ctx.strip():
        return {"response": REFUSAL_MSG}

    try:
        from modules.ai_extraction.client import OllamaClient
        client = OllamaClient()
        
        system_prompt = (
            "You are the Debt Detox AI Loan Assistant. Your ONLY task is to answer user questions using strictly and exclusively the uploaded loan document context provided below.\n\n"
            "STRICT RULES:\n"
            "1. Answer ONLY questions directly related to the currently uploaded loan document.\n"
            "2. Fetch answers strictly and exclusively from the provided document context.\n"
            "3. If the answer is not present in the uploaded document, clearly say: \"This information is not available in the uploaded document\".\n"
            "4. Do NOT use general knowledge, assumptions, hallucinations, outside financial advice, or external information under any circumstances.\n\n"
            f"--- CONTRACT CONTEXT ---\n{inputs.context_text}\n-----------------------\n"
        )
        
        # Format conversation history
        conversation_prompt = ""
        for h in inputs.history:
            role = "User" if h.get("role") == "user" else "Assistant"
            conversation_prompt += f"{role}: {h.get('content')}\n"
        conversation_prompt += f"User: {inputs.message}\nAssistant:"
        
        # Call LLM. OllamaClient's generate_json expects system prompt and returns JSON.
        prompt = (
            f"{conversation_prompt}\n"
            "Respond in JSON format: {\"response\": \"your clear answer strictly from context or \\\"This information is not available in the uploaded document\\\"\"}"
        )
        
        res = client.generate_json(prompt, system_prompt)
        if isinstance(res, dict) and "response" in res:
            ans = res["response"].strip()
            if ans:
                return {"response": ans}
            
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        
    # Fallback QA Engine
    msg = inputs.message.lower().strip()
    ctx_lower = ctx.lower()
    
    if any(w in msg for w in ["fee", "hidden", "charge", "cost"]):
        if "extracted charges:" in ctx_lower:
            charges_part = ctx.split("Extracted Charges:")[1].split("Regulatory Warnings:")[0].strip()
            if charges_part and charges_part != "None":
                return {"response": f"Here are the charges extracted from your document:\n\n{charges_part}"}
        lines = [l for l in ctx.split("\n") if any(k in l.lower() for k in ["fee", "charge", "cost"])]
        if lines:
            return {"response": "Here are the charge details in your document:\n\n" + "\n".join(lines)}
            
    if "insurance" in msg:
        if "insurance" in ctx_lower:
            lines = [l for l in ctx.split("\n") if "insurance" in l.lower()]
            if lines:
                return {"response": "Here are the insurance details in your document:\n\n" + "\n".join(lines)}
        return {"response": REFUSAL_MSG}

    if any(w in msg for w in ["penalty", "late", "prepay", "foreclos", "bounce"]):
        lines = [l for l in ctx.split("\n") if any(k in l.lower() for k in ["penalty", "late", "prepay", "foreclos", "bounce"])]
        if lines:
            return {"response": "Here are the penalty clauses identified in your contract:\n\n" + "\n".join(lines)}
            
    if any(w in msg for w in ["warning", "alert", "compliance", "rbi", "risk"]):
        if "regulatory warnings:" in ctx_lower:
            alerts_part = ctx.split("Regulatory Warnings:")[1].strip()
            if alerts_part and alerts_part != "None":
                return {"response": "Here are the regulatory compliance warnings for your contract:\n\n" + alerts_part}
            
    if any(w in msg for w in ["interest", "rate", "emi", "tenure", "amount", "sanction", "principal", "lender", "borrower"]):
        summary_lines = [line for line in ctx.split("\n") if any(k in line.lower() for k in ["amount", "interest", "rate", "tenure", "emi", "sanction", "principal", "lender", "borrower"])]
        if summary_lines:
            return {"response": "Here are the primary financial terms from your contract:\n\n" + "\n".join(summary_lines)}
            
    for line in ctx.split("\n"):
        line_clean = line.strip()
        if line_clean and len(line_clean) > 5 and any(word in line_clean.lower() for word in msg.split() if len(word) > 3 and word in line_clean.lower()):
            return {"response": f"Document details:\n\n{line_clean}"}

    return {"response": REFUSAL_MSG}


# Host React production builds static folder
frontend_dist = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
    logger.info("Serving React frontend static assets from frontend/dist")
else:
    logger.warning("React production build 'frontend/dist' folder not found. Start Vite development server separately.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True, reload_excludes=["uploads/*", "**/uploads/**", "*.log"])
