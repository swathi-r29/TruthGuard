import streamlit as st
from modules.ai_extraction.schemas import LoanExtractionResult

def render_evidence_page():
    st.markdown(
        """
        <div style="margin-bottom: 25px;">
            <h1 style="margin: 0; background: linear-gradient(135deg, #ffffff 0%, #a5b4fc 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 32px; font-weight: 800; font-family: 'Space Grotesk', sans-serif;">🔎 Verification Trace & Evidence Audit</h1>
            <p style="margin: 5px 0 0 0; color: #94a3b8; font-size: 14px; line-height: 1.6;">
                To prevent hallucination, Debt Detox requires every extracted loan parameter to be backed by verifiable text snippets directly from your agreement. Below is the complete trace log.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    audit_status = st.session_state.get("audit_status", "FAILED")
    
    if audit_status == "FAILED":
        st.markdown(
            f"""
            <div class="premium-card glow-border-rose" style="background: rgba(239, 68, 68, 0.03); padding: 24px;">
                <div style="font-weight: 700; color: #EF4444; font-size: 16px; margin-bottom: 8px;">❌ Analysis incomplete — extraction failed.</div>
                <div style="color: #cbd5e1; font-size: 13px; line-height: 1.5;">
                    The document content could not be successfully parsed or terms extracted. Review the verification trace and confirm your AI engine settings.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        return

    # Check for Partial analysis
    if audit_status == "PARTIAL":
        st.markdown(
            f"""
            <div class="premium-card glow-border-amber" style="background: rgba(245, 158, 11, 0.02); padding: 20px; margin-bottom: 25px;">
                <div style="font-weight: 700; color: #f59e0b; font-size: 15px; margin-bottom: 5px;">⚠️ Partial Analysis Warning</div>
                <div style="color: #cbd5e1; font-size: 12px; line-height: 1.4;">
                    Some core loan terms (Principal, Rate, or Tenure) could not be extracted directly from this document.
                    Debt Detox is running with estimated values or partial inputs where available. Please verify missing details with your lender.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    if "extracted" not in st.session_state or st.session_state.extracted is None:
        st.markdown(
            """
            <div class="premium-card glow-border-amber" style="background: rgba(245, 158, 11, 0.02); padding: 24px; margin-bottom: 25px;">
                <div style="font-weight: 700; color: #f59e0b; font-size: 16px; margin-bottom: 8px;">⚠️ No Document Analyzed Yet</div>
                <div style="color: #cbd5e1; font-size: 13px; line-height: 1.5;">
                    Please go to the <b>Upload & Analyze</b> page and process a loan agreement to view the verification trace.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        return

    extracted = st.session_state.extracted
    charges = st.session_state.charges or []
    currency = "₹"

    # Compile all records for trace table
    records = []
    schema_fields = LoanExtractionResult.model_fields.keys()
    
    for field_name in schema_fields:
        if field_name == "other_charges":
            continue
            
        field_data = getattr(extracted, field_name, None)
        if field_data:
            val = field_data.value
            page = field_data.page
            evidence = field_data.evidence
            confidence = field_data.confidence or "medium"
            status = getattr(field_data, "status", None)
            orig_term = getattr(field_data, "original_term", None) or field_name.replace("_", " ").title()
            
            if not status:
                if val is not None and str(val).lower() != 'null':
                    status = "VERIFIED"
                elif evidence:
                    status = "MENTIONED-BUT-NOT-SPECIFIED"
                else:
                    status = "NOT FOUND"
                    
            disp_val = f"{val} ({field_data.unit or 'raw'})" if val is not None else ("Mentioned — Value Not Specified" if status == "MENTIONED-BUT-NOT-SPECIFIED" else "Not Found")
            
            if status != "NOT FOUND" or field_name in ["loan_amount", "interest_rate", "tenure", "emi"]:
                records.append({
                    "Field": orig_term,
                    "Extracted Value": disp_val,
                    "Page": page if page is not None else 1,
                    "Evidence Snippet": evidence or "No verifiable evidence found in the document.",
                    "Confidence": confidence,
                    "Raw Value": val,
                    "Source": "native_text" if not getattr(st.session_state, "ocr_used", False) else "ocr_fallback",
                    "Status": status
                })
                
    # Add other charges from AI extraction
    for idx, charge in enumerate(extracted.other_charges):
        status = getattr(charge, "status", "VERIFIED" if charge.value is not None else "MENTIONED-BUT-NOT-SPECIFIED")
        disp_val = f"{charge.value} ({charge.unit or 'raw'})" if charge.value is not None else "Mentioned — Value Not Specified"
        records.append({
            "Field": f"Other Charge: {charge.name}",
            "Extracted Value": disp_val,
            "Page": charge.page if charge.page is not None else 1,
            "Evidence Snippet": charge.evidence or "No verifiable evidence found in the document.",
            "Confidence": charge.confidence or "medium",
            "Raw Value": charge.value,
            "Source": "native_text",
            "Status": status
        })
        
    # Add keyword charges
    kw_charges = [c for c in charges if c.get("source") == "keyword_reference"]
    for c in kw_charges:
        name = c.get("original_name") or c.get("canonical_name").replace("_", " ").title()
        records.append({
            "Field": name,
            "Extracted Value": "Mentioned — Value Not Specified",
            "Page": c.get("page", 1),
            "Evidence Snippet": c.get("evidence") or "No verifiable evidence found in the document.",
            "Confidence": "medium",
            "Raw Value": None,
            "Source": "keyword_reference",
            "Status": "MENTIONED-BUT-NOT-SPECIFIED"
        })
        
    # Append Not Found items for core catalog terms if missing
    catalog_term_names = {
        "processing_fee": "Processing Fee",
        "insurance": "Credit Insurance",
        "documentation_fee": "Documentation / Stamp Duty",
        "gst_tax_references": "GST / Tax Clauses",
        "foreclosure_charge": "Foreclosure Charges",
        "prepayment_charge": "Prepayment Charges",
        "late_payment_fee": "Late Payment Penalty",
        "bounce_charge": "ECS / Bounce Charge"
    }
    
    for key, disp_name in catalog_term_names.items():
        already_added = any(disp_name.lower() in r["Field"].lower() for r in records)
        if not already_added:
            records.append({
                "Field": disp_name,
                "Extracted Value": "Not Found",
                "Page": "-",
                "Evidence Snippet": "No verifiable evidence found in the document.",
                "Confidence": "-",
                "Raw Value": None,
                "Source": "-",
                "Status": "NOT FOUND"
            })

    if not records:
        st.markdown(
            """
            <div class="premium-card glow-border-rose" style="background: rgba(239, 68, 68, 0.02); padding: 20px;">
                <div style="color: #cbd5e1; font-size: 13px;">No verifiable evidence found in the document.</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        return

    # Render HTML Trace Table
    st.markdown(
        """
        <h4 style="margin-top: 15px; margin-bottom: 15px; font-size: 15px; font-family: 'Space Grotesk', sans-serif; font-weight: 700; color: #ffffff;">📋 Verification Trace Matrix</h4>
        """,
        unsafe_allow_html=True
    )
    
    rows_html = ""
    for r in records:
        status = r["Status"]
        if status == "Verified":
            status_color = "#10b981"
        elif status == "Keyword Detected":
            status_color = "#f59e0b"
        elif status == "Needs Review":
            status_color = "#EF4444"
        else:
            status_color = "#94a3b8"
        
        rows_html += f"""
        <tr style="border-bottom: 1px solid rgba(148,163,184,0.1); color: #cbd5e1; font-size: 12px;">
            <td style="padding: 10px 14px; font-weight: 600; color: #ffffff;">{r['Field']}</td>
            <td style="padding: 10px 14px;"><code>{r['Extracted Value']}</code></td>
            <td style="padding: 10px 14px; text-align: center;">{f'Page {r["Page"]}' if isinstance(r["Page"], int) else r["Page"]}</td>
            <td style="padding: 10px 14px; text-align: center; font-weight: 700; text-transform: uppercase;">{r['Confidence']}</td>
            <td style="padding: 10px 14px; text-align: right;"><span style="color: {status_color}; font-weight: 700;">{status}</span></td>
        </tr>
        """
        
    st.markdown(
        f"""
        <div style="overflow-x: auto; margin-bottom: 25px; border-radius: 8px; border: 1px solid rgba(148,163,184,0.15);">
            <table style="width:100%; border-collapse: collapse; background: #0F1E33; text-align: left;">
                <thead>
                    <tr style="background: #13253D; border-bottom: 1px solid rgba(148,163,184,0.15); color: #F8FAFC; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;">
                        <th style="padding: 12px 14px;">Term</th>
                        <th style="padding: 12px 14px;">Extracted Value</th>
                        <th style="padding: 12px 14px; text-align: center;">Evidence Page</th>
                        <th style="padding: 12px 14px; text-align: center;">Confidence</th>
                        <th style="padding: 12px 14px; text-align: right;">Status</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Detailed Audit Snippets
    st.markdown(
        """
        <h4 style="margin-top: 30px; margin-bottom: 15px; font-size: 15px; font-family: 'Space Grotesk', sans-serif; font-weight: 700; color: #ffffff;">🔍 Verifiable Document Snippets</h4>
        <p style="margin: -10px 0 20px 0; color: #94a3b8; font-size: 12px;">Expand any parameter below to inspect the verbatim clause text and matching highlight.</p>
        """,
        unsafe_allow_html=True
    )
    
    for r in records:
        status = r["Status"]
        if status == "Not Found":
            continue
            
        conf_color = "#10b981" if r["Confidence"] == "high" else ("#f59e0b" if r["Confidence"] == "medium" else "#f43f5e")
        if status == "Verified":
            status_color = "#10b981"
        elif status == "Keyword Detected":
            status_color = "#f59e0b"
        else:
            status_color = "#ef4444"
        
        from modules.explanation.explainer import get_simple_explanation, generate_math_example
        explanation = get_simple_explanation(r['Field'], r["Evidence Snippet"])
        math_eg = generate_math_example(r['Field'], r.get("Raw Value"), None, None)
        
        math_html = ""
        if math_eg:
            res_val = math_eg.get('result')
            res_str = f"₹{res_val:,.2f}" if isinstance(res_val, (int, float)) else str(res_val)
            math_html = f"""
            <div style="background: rgba(99, 102, 241, 0.05); border: 1px solid rgba(99, 102, 241, 0.15); border-radius: 6px; padding: 10px; margin-bottom: 10px; font-size: 12px; color: #cbd5e1;">
                💡 <b>Math Impact Scenario ({math_eg.get('scenario', 'Calculation')}):</b> {math_eg.get('formula', '')} = <b>{res_str}</b>
            </div>
            """

        with st.expander(f"🔎 Audit Details: {r['Field']} ({status})"):
            snippet = r["Evidence Snippet"]
            highlighted_snippet = snippet
            val_str = str(r["Raw Value"]) if r.get("Raw Value") is not None else ""
            if val_str and val_str in snippet:
                highlighted_snippet = snippet.replace(val_str, f"<span style='background-color: rgba(56, 189, 248, 0.25); color: #38BDF8; font-weight: 700; padding: 2px 6px; border-radius: 4px;'>{val_str}</span>")
            
            st.markdown(
                f"""
                <div style="background-color: rgba(0, 0, 0, 0.25); padding: 16px; border-radius: 8px; font-size: 13px; color: #cbd5e1; border: 1px solid rgba(148,163,184,0.1); font-family: monospace; line-height: 1.6; font-style: italic; margin-bottom: 10px;">
                    "{highlighted_snippet}"
                </div>
                <div style="background: rgba(56, 189, 248, 0.04); border-left: 3px solid #38bdf8; padding: 10px 14px; border-radius: 6px; font-size: 12px; color: #f8fafc; margin-bottom: 10px; line-height: 1.5;">
                    <b>Plain-English Explainability Rationale:</b> {explanation}
                </div>
                {math_html}
                <div style="display: flex; justify-content: space-between; font-size: 11px; color: #94a3b8; padding: 4px 4px 0 4px;">
                    <span>Extraction Method: <b>{r['Source'].replace('_', ' ').title()}</b></span>
                    <span>Confidence Score: <b style="color: {conf_color}; text-transform: uppercase;">{r['Confidence']}</b></span>
                </div>
                """,
                unsafe_allow_html=True
            )

