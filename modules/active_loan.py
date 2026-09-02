"""
Single Source of Truth helper for ACTIVE_LOAN in Debt Detox.
Maintains st.session_state["ACTIVE_LOAN"] and synchronizes with legacy session state keys.
"""

from typing import Dict, Any, List, Optional
from modules.analyzer.compliance import check_regulatory_compliance

def set_active_loan(
    st_session: Any,
    doc_name: str,
    doc_type: str,
    total_pages: int,
    ocr_used: bool,
    extracted: Any,
    charges: List[Dict[str, Any]],
    metrics: Dict[str, Any],
    effective_rates: Optional[Dict[str, Any]] = None,
    transparency: Optional[Dict[str, Any]] = None,
    explanations: Optional[Dict[str, Any]] = None,
    math_examples: Optional[Dict[str, Any]] = None,
    audit_status: str = "VERIFIED",
    data_source_badge: str = "DATA SOURCE: CURRENT UPLOADED DOCUMENT"
) -> Dict[str, Any]:
    """
    Sets the ACTIVE_LOAN object in st_session and syncs flat legacy session keys.
    Returns the newly constructed ACTIVE_LOAN dictionary.
    """
    # Calculate compliance alerts dynamically
    compliance_alerts = check_regulatory_compliance(metrics or {}, charges or [])

    active_loan_data = {
        "doc_name": doc_name,
        "doc_type": doc_type,
        "total_pages": total_pages,
        "ocr_used": ocr_used,
        "extracted": extracted,
        "charges": charges or [],
        "metrics": metrics or {},
        "effective_rates": effective_rates or {},
        "transparency": transparency or {},
        "explanations": explanations or {},
        "math_examples": math_examples or {},
        "compliance_alerts": compliance_alerts or [],
        "audit_status": audit_status,
        "data_source_badge": data_source_badge,
    }

    # Store in session state under single source of truth key
    st_session["ACTIVE_LOAN"] = active_loan_data

    # Synchronize legacy flat session state attributes for backwards compatibility
    legacy_keys = {
        "doc_name": doc_name,
        "doc_type": doc_type,
        "total_pages": total_pages,
        "ocr_used": ocr_used,
        "extracted": extracted,
        "charges": charges,
        "metrics": metrics,
        "effective_rates": effective_rates,
        "transparency": transparency,
        "explanations": explanations,
        "math_examples": math_examples,
        "audit_status": audit_status,
        "data_source_badge": data_source_badge,
        "compliance_alerts": compliance_alerts
    }

    for k, v in legacy_keys.items():
        st_session[k] = v
        try:
            setattr(st_session, k, v)
        except Exception:
            pass

    return active_loan_data


def get_active_loan(st_session: Any) -> Optional[Dict[str, Any]]:
    """
    Retrieves the ACTIVE_LOAN dictionary from st_session.
    If not explicitly present under 'ACTIVE_LOAN', builds it from flat session keys if available.
    """
    if "ACTIVE_LOAN" in st_session and st_session["ACTIVE_LOAN"] is not None:
        return st_session["ACTIVE_LOAN"]

    # Fallback assembly from legacy flat keys if present
    metrics = getattr(st_session, "metrics", None)
    if metrics:
        charges = getattr(st_session, "charges", []) or []
        compliance_alerts = getattr(st_session, "compliance_alerts", None)
        if compliance_alerts is None:
            compliance_alerts = check_regulatory_compliance(metrics, charges)

        loan_dict = {
            "doc_name": getattr(st_session, "doc_name", "Unknown Document"),
            "doc_type": getattr(st_session, "doc_type", "pdf"),
            "total_pages": getattr(st_session, "total_pages", 1),
            "ocr_used": getattr(st_session, "ocr_used", False),
            "extracted": getattr(st_session, "extracted", None),
            "charges": charges,
            "metrics": metrics,
            "effective_rates": getattr(st_session, "effective_rates", {}) or {},
            "transparency": getattr(st_session, "transparency", {}) or {},
            "explanations": getattr(st_session, "explanations", {}) or {},
            "math_examples": getattr(st_session, "math_examples", {}) or {},
            "compliance_alerts": compliance_alerts,
            "audit_status": getattr(st_session, "audit_status", "VERIFIED"),
            "data_source_badge": getattr(st_session, "data_source_badge", "DATA SOURCE: CURRENT UPLOADED DOCUMENT")
        }
        st_session["ACTIVE_LOAN"] = loan_dict
        return loan_dict

    return None
