import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def generate_amortization_schedule(principal: float, annual_rate: float, tenure: float, emi: float):
    schedule = []
    outstanding = principal
    monthly_rate = (annual_rate / 100.0) / 12.0
    
    for month in range(1, int(tenure) + 1):
        if outstanding <= 0:
            break
        interest = outstanding * monthly_rate
        p_pay = emi - interest
        if p_pay > outstanding or month == int(tenure):
            p_pay = outstanding
            actual_emi = p_pay + interest
        else:
            actual_emi = emi
            
        outstanding_new = outstanding - p_pay
        schedule.append({
            "Month": month,
            "EMI": actual_emi,
            "Interest Paid": interest,
            "Principal Repaid": p_pay,
            "Outstanding Balance": max(0.0, outstanding_new)
        })
        outstanding = outstanding_new
        
    return schedule

def render_dashboard_page():
    st.markdown(
        """
        <div style="margin-bottom: 25px;">
            <h1 style="margin: 0; background: linear-gradient(135deg, #ffffff 0%, #a5b4fc 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 32px; font-weight: 800; font-family: 'Space Grotesk', sans-serif;">📊 Loan Truth Dashboard</h1>
            <p style="margin: 5px 0 0 0; color: #94a3b8; font-size: 14px; line-height: 1.6;">
                A comprehensive structural breakdown of your agreement terms, comparing stated interest rates against the real effective APR.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Check if document has been uploaded and analyzed
    if "metrics" not in st.session_state or st.session_state.metrics is None:
        st.markdown(
            """
            <div class="premium-card glow-border-amber" style="background: rgba(245, 158, 11, 0.03);">
                <div style="font-weight: 700; color: #f59e0b; font-size: 14px; margin-bottom: 5px;">⚠️ No Document Analyzed Yet</div>
                <div style="color: #cbd5e1; font-size: 12px;">Please go to the <b>Upload & Analyze</b> page and process a loan agreement to view the dashboard.</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        return

    metrics = st.session_state.metrics or {}
    effective_rates = st.session_state.get("effective_rates") or {}
    transparency = st.session_state.get("transparency") or {}
    doc_name = st.session_state.doc_name
    doc_type = st.session_state.doc_type
    total_pages = st.session_state.total_pages
    ocr_used = st.session_state.ocr_used
    
    currency = "₹"
    
    audit_status = st.session_state.get("audit_status", "FAILED")
    
    if audit_status == "FAILED":
        st.markdown(
            f"""
            <div class="premium-card glow-border-rose" style="padding: 16px 20px; display: flex; justify-content: space-between; align-items: center; background: rgba(239, 68, 68, 0.02); margin-bottom: 25px;">
                <div>
                    <h4 style="margin: 0; color: #ffffff; font-size: 16px; font-weight: 700; font-family: 'Space Grotesk', sans-serif;">📄 {doc_name}</h4>
                    <div style="margin-top: 4px; color: #94a3b8; font-size: 11px;">
                        Type: <b style="color: #cbd5e1;">{doc_type.upper()}</b> &nbsp;|&nbsp; Pages: <b style="color: #cbd5e1;">{total_pages}</b> &nbsp;|&nbsp; OCR Fallback: <b style="color: {'#10b981' if ocr_used else '#94a3b8'};">{'Active' if ocr_used else 'Inactive'}</b>
                    </div>
                </div>
                <div style="background: rgba(239, 68, 68, 0.1); color: #EF4444; font-size: 10px; font-weight: 800; padding: 6px 12px; border-radius: 20px; border: 1px solid rgba(239, 68, 68, 0.2); letter-spacing: 0.05em; text-transform: uppercase;">
                    Audit Failed
                </div>
            </div>
            
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

    # Compile executive summary metrics
    extracted = st.session_state.extracted
    charges = st.session_state.charges
    score = transparency["score"]
    
    # Compile terms status list
    terms_status = []
    
    # Helper to check if a charge exists in the detected list
    def get_charge_val_or_keyword(canonical_name, display_name):
        # Check in extracted fields first
        field_data = getattr(extracted, canonical_name, None)
        if field_data and field_data.value is not None and str(field_data.value).lower() != 'null':
            val = field_data.value
            if isinstance(val, (int, float)):
                val_str = f"{currency}{val:,.2f}" if field_data.unit == "currency" else f"{val} {field_data.unit or ''}"
            else:
                val_str = str(val).strip()
                if field_data.unit == "currency":
                    try:
                        clean_val = val_str.replace(',', '').replace('Rs.', '').replace('INR', '').strip()
                        val_str = f"{currency}{float(clean_val):,.2f}"
                    except ValueError:
                        if currency not in val_str and "Rs" not in val_str and "INR" not in val_str:
                            val_str = f"{currency}{val_str}"
                else:
                    if field_data.unit:
                        val_str = f"{val_str} {field_data.unit}"
            return {"name": display_name, "status": "VERIFIED", "value": val_str, "evidence": field_data.evidence}
            
        # Fallback to detected charges list (maybe keyword matched)
        matching_charges = [c for c in charges if c["canonical_name"] == canonical_name]
        if matching_charges:
            first = matching_charges[0]
            if first.get("value") is not None:
                val = first.get("value")
                if isinstance(val, (int, float)):
                    val_str = f"{val}%" if first.get("unit") == "percent" else f"{currency}{val:,.2f}"
                else:
                    val_str = str(val).strip()
                    try:
                        clean_val = val_str.replace(',', '').replace('Rs.', '').replace('INR', '').replace('%', '').strip()
                        float_val = float(clean_val)
                        if first.get("unit") == "percent":
                            val_str = f"{float_val}%"
                        else:
                            val_str = f"{currency}{float_val:,.2f}"
                    except ValueError:
                        if first.get("unit") == "percent" and "%" not in val_str:
                            val_str = f"{val_str}%"
                        elif first.get("unit") == "currency" and currency not in val_str and "Rs" not in val_str and "INR" not in val_str:
                            val_str = f"{currency}{val_str}"
                return {"name": display_name, "status": "VERIFIED", "value": val_str, "evidence": first.get("evidence")}
            else:
                return {"name": display_name, "status": "KEYWORD DETECTED", "value": "Mentioned, Value Not Specified", "evidence": first.get("evidence")}
                
        return {"name": display_name, "status": "NOT FOUND", "value": "Not Specified", "evidence": None}
        
    terms_status.append(get_charge_val_or_keyword("processing_fee", "Processing Fee"))
    terms_status.append(get_charge_val_or_keyword("insurance", "Credit Insurance"))
    terms_status.append(get_charge_val_or_keyword("documentation_fee", "Documentation / Stamp Duty"))
    terms_status.append(get_charge_val_or_keyword("gst_tax_references", "GST / Tax Clauses"))
    terms_status.append(get_charge_val_or_keyword("foreclosure_charge", "Foreclosure Charges"))
    terms_status.append(get_charge_val_or_keyword("prepayment_charge", "Prepayment Charges"))
    terms_status.append(get_charge_val_or_keyword("late_payment_fee", "Late Payment Penalty"))
    terms_status.append(get_charge_val_or_keyword("bounce_charge", "ECS / Bounce Charge"))

    # Count terms
    num_verified = sum(1 for t in terms_status if t["status"] == "VERIFIED")
    num_keywords = sum(1 for t in terms_status if t["status"] == "KEYWORD DETECTED")
    num_missing = sum(1 for t in terms_status if t["status"] == "NOT FOUND")
    
    # Calculate overall confidence
    conf_values = []
    schema_fields = list(extracted.model_fields.keys())
    for field_name in schema_fields:
        if field_name == "other_charges":
            continue
        field_data = getattr(extracted, field_name)
        if field_data and field_data.value is not None and str(field_data.value).lower() != 'null':
            conf = field_data.confidence or "medium"
            conf_values.append(0.95 if conf == "high" else (0.80 if conf == "medium" else 0.50))
    for c in extracted.other_charges:
        if c.value is not None:
            conf = c.confidence or "medium"
            conf_values.append(0.95 if conf == "high" else (0.80 if conf == "medium" else 0.50))
            
    overall_conf_pct = int(sum(conf_values) / len(conf_values) * 100) if conf_values else 0
    overall_conf_str = f"{overall_conf_pct}%" if overall_conf_pct > 0 else "N/A"
    
    status_color = "#10B981" if audit_status == "VERIFIED" else "#F59E0B"
    score_color = "#10b981" if score >= 80 else ("#f59e0b" if score >= 60 else "#f43f5e")

    # Header summary card
    st.markdown(
        f"""
        <div style="background: #0F1E33; border: 1px solid rgba(148,163,184,0.15); border-radius: 16px; padding: 20px; margin-bottom: 25px; box-shadow: 0 4px 20px rgba(0,0,0,0.25);">
            <div style="font-size: 10px; color: #94A3B8; text-transform: uppercase; font-weight: 700; letter-spacing: 0.08em; margin-bottom: 15px; border-bottom: 1px solid rgba(148,163,184,0.15); padding-bottom: 10px; display: flex; justify-content: space-between;">
                <span>🛡️ Audit Summary: {doc_name}</span>
                <span style="color: #cbd5e1;">Pages: {total_pages}</span>
            </div>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(110px, 1fr)); gap: 15px; text-align: center;">
                <div>
                    <div style="font-size: 9px; color: #94A3B8; text-transform: uppercase; font-weight: 700; margin-bottom: 4px;">Extraction Status</div>
                    <div style="font-size: 13.5px; font-weight: 800; color: {status_color}; text-transform: uppercase;">{audit_status}</div>
                </div>
                <div>
                    <div style="font-size: 9px; color: #94A3B8; text-transform: uppercase; font-weight: 700; margin-bottom: 4px;">OCR Status</div>
                    <div style="font-size: 13.5px; font-weight: 800; color: {'#10b981' if ocr_used else '#94a3b8'};">{'ACTIVE' if ocr_used else 'BYPASSED'}</div>
                </div>
                <div>
                    <div style="font-size: 9px; color: #94A3B8; text-transform: uppercase; font-weight: 700; margin-bottom: 4px;">Verified Terms</div>
                    <div style="font-size: 15px; font-weight: 800; color: #10b981;">{num_verified}</div>
                </div>
                <div>
                    <div style="font-size: 9px; color: #94A3B8; text-transform: uppercase; font-weight: 700; margin-bottom: 4px;">Keywords</div>
                    <div style="font-size: 15px; font-weight: 800; color: #f59e0b;">{num_keywords}</div>
                </div>
                <div>
                    <div style="font-size: 9px; color: #94A3B8; text-transform: uppercase; font-weight: 700; margin-bottom: 4px;">Missing/Unverified</div>
                    <div style="font-size: 15px; font-weight: 800; color: #EF4444;">{num_missing}</div>
                </div>
                <div>
                    <div style="font-size: 9px; color: #94A3B8; text-transform: uppercase; font-weight: 700; margin-bottom: 4px;">Overall Confidence</div>
                    <div style="font-size: 15px; font-weight: 800; color: #38BDF8;">{overall_conf_str}</div>
                </div>
                <div>
                    <div style="font-size: 9px; color: #94A3B8; text-transform: uppercase; font-weight: 700; margin-bottom: 4px;">Transparency Score</div>
                    <div style="font-size: 15px; font-weight: 800; color: {score_color};">{score}/100</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Row 1: Key Core Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    def render_custom_metric(col, label, value, icon, accent_color):
        with col:
            st.markdown(
                f"""
                <div class="premium-card" style="padding: 20px; min-height: 110px; display: flex; flex-direction: column; justify-content: space-between; background: rgba(255,255,255,0.015);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span style="font-size: 11px; color: #94a3b8; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;">{label}</span>
                        <span style="font-size: 18px; color: {accent_color};">{icon}</span>
                    </div>
                    <div style="font-size: 22px; font-weight: 800; color: #ffffff; font-family: 'Outfit', sans-serif;">{value}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
            
    render_custom_metric(col1, "Principal Amount", f"{currency}{metrics['loan_amount']:,.2f}", "💰", "#6366f1")
    render_custom_metric(col2, "Stated Interest Rate", f"{metrics['interest_rate_annual']}% p.a.", "📈", "#06b6d4")
    render_custom_metric(col3, "Loan Tenure", f"{metrics['tenure_months']} Months", "📅", "#8b5cf6")
    render_custom_metric(col4, "Scheduled Monthly EMI", f"{currency}{metrics['emi']:,.2f}", "💸", "#10b981")

    # Row 2: Real Borrowing Costs (The "Truth")
    st.markdown(
        """
        <h3 style="margin-top: 30px; margin-bottom: 20px; font-size: 18px; font-family: 'Space Grotesk', sans-serif; font-weight: 700;">🔍 The Financial Reality</h3>
        """,
        unsafe_allow_html=True
    )
    col_a, col_b, col_c = st.columns(3)
    
    with col_a:
        net_disbursed = metrics['net_disbursed_amount']
        st.markdown(
            f"""
            <div class="premium-card glow-border-emerald" style="text-align: center; background: rgba(16, 185, 129, 0.01); height: 160px; display: flex; flex-direction: column; justify-content: center;">
                <h5 style="margin: 0; color: #94a3b8; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;">Disbursement Amount</h5>
                <h2 style="margin: 10px 0; color: #10b981; font-size: 26px; font-weight: 800; font-family: 'Outfit', sans-serif;">{currency}{net_disbursed:,.2f}</h2>
                <p style="margin: 0; font-size: 11px; color: #94a3b8; line-height: 1.4;">
                    What you actually receive after upfront deductions.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        
    with col_b:
        total_cost = metrics['scheduled_total_cost']
        st.markdown(
            f"""
            <div class="premium-card glow-border-rose" style="text-align: center; background: rgba(244, 63, 94, 0.01); height: 160px; display: flex; flex-direction: column; justify-content: center;">
                <h5 style="margin: 0; color: #94a3b8; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;">Real Scheduled Cost</h5>
                <h2 style="margin: 10px 0; color: #f43f5e; font-size: 26px; font-weight: 800; font-family: 'Outfit', sans-serif;">{currency}{total_cost:,.2f}</h2>
                <p style="margin: 0; font-size: 11px; color: #94a3b8; line-height: 1.4;">
                    Total interest + processing/upfront fees + taxes.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        
    with col_c:
        eff_rate = effective_rates.get('effective_annual_cost_rate') if isinstance(effective_rates, dict) else None
        rate_val = f"{eff_rate:.2f}%" if eff_rate is not None else "N/A"
        st.markdown(
            f"""
            <div class="premium-card glow-border-cyan" style="text-align: center; background: rgba(6, 182, 212, 0.01); height: 160px; display: flex; flex-direction: column; justify-content: center;">
                <h5 style="margin: 0; color: #94a3b8; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;">Effective Cost Rate (APR)</h5>
                <h2 style="margin: 10px 0; color: #06b6d4; font-size: 26px; font-weight: 800; font-family: 'Outfit', sans-serif;">{rate_val}</h2>
                <p style="margin: 0; font-size: 11px; color: #94a3b8; line-height: 1.4;">
                    The real annual rate taking upfront fees into account.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        
    # Comprehensive APR Calculation & Mathematical Audit Transparency
    p = float(metrics.get('loan_amount', 0.0) or 0.0)
    net = float(metrics.get('net_disbursed_amount', 0.0) or 0.0)
    nominal = float(metrics.get('interest_rate_annual', 0.0) or 0.0)
    eff_rate = effective_rates.get('effective_annual_cost_rate') if isinstance(effective_rates, dict) else None
    upfront = float(metrics.get('upfront_fees', 0.0) or 0.0)
    taxes = float(metrics.get('taxes_on_fees', 0.0) or 0.0)
    tot_deductions = upfront + taxes
    currency = "₹"

    st.markdown(
        """
        <h3 style="margin-top: 35px; margin-bottom: 15px; font-size: 18px; font-family: 'Space Grotesk', sans-serif; font-weight: 700; color: #F8FAFC;">
            🧮 APR Calculation & Mathematical Audit Transparency
        </h3>
        """,
        unsafe_allow_html=True
    )

    with st.expander("📊 Step-by-Step Mathematical Audit & Formula Breakdown", expanded=True):
        st.markdown(
            f"""
            <div style="background: #0A1628; border: 1px solid rgba(148,163,184,0.15); border-radius: 12px; padding: 20px; margin-bottom: 15px;">
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px;">
                    <div style="background: rgba(99, 102, 241, 0.05); padding: 14px; border-radius: 10px; border: 1px solid rgba(99, 102, 241, 0.2);">
                        <div style="font-size: 11px; color: #94A3B8; font-weight: 700; text-transform: uppercase;">1. Sanctioned Principal (P)</div>
                        <div style="font-size: 20px; font-weight: 800; color: #6366F1; margin-top: 4px;">{currency}{p:,.2f}</div>
                        <div style="font-size: 11px; color: #cbd5e1; margin-top: 2px;">Contract face value</div>
                    </div>
                    <div style="background: rgba(239, 68, 68, 0.05); padding: 14px; border-radius: 10px; border: 1px solid rgba(239, 68, 68, 0.2);">
                        <div style="font-size: 11px; color: #94A3B8; font-weight: 700; text-transform: uppercase;">2. Upfront Deductions (D)</div>
                        <div style="font-size: 20px; font-weight: 800; color: #EF4444; margin-top: 4px;">-{currency}{tot_deductions:,.2f}</div>
                        <div style="font-size: 11px; color: #cbd5e1; margin-top: 2px;">Processing + Stamp Duty + GST</div>
                    </div>
                    <div style="background: rgba(16, 185, 129, 0.05); padding: 14px; border-radius: 10px; border: 1px solid rgba(16, 185, 129, 0.2);">
                        <div style="font-size: 11px; color: #94A3B8; font-weight: 700; text-transform: uppercase;">3. Net Disbursed Cash (N)</div>
                        <div style="font-size: 20px; font-weight: 800; color: #10B981; margin-top: 4px;">{currency}{net:,.2f}</div>
                        <div style="font-size: 11px; color: #cbd5e1; margin-top: 2px;">Actual payout received</div>
                    </div>
                    <div style="background: rgba(56, 189, 248, 0.05); padding: 14px; border-radius: 10px; border: 1px solid rgba(56, 189, 248, 0.2);">
                        <div style="font-size: 11px; color: #94A3B8; font-weight: 700; text-transform: uppercase;">4. Real Effective APR</div>
                        <div style="font-size: 20px; font-weight: 800; color: #38BDF8; margin-top: 4px;">{f'{eff_rate:.2f}%' if eff_rate is not None else 'N/A'}</div>
                        <div style="font-size: 11px; color: #cbd5e1; margin-top: 2px;">Advertised Nominal: {nominal}%</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("**📐 Actuarial Formula & IRR Cash Flow Equation:**")
        st.latex(r"\text{Net Disbursed Cash } N = \sum_{t=1}^{n} \frac{\text{EMI}_t}{(1 + r_{\text{monthly}})^t}")
        st.latex(r"\text{Effective APR} = \left((1 + r_{\text{monthly}})^{12} - 1\right) \times 100\%")

        if eff_rate is not None and nominal > 0:
            diff = eff_rate - nominal
            if diff > 0.05:
                st.markdown(
                    f"""
                    <div class="premium-card glow-border-amber" style="background: rgba(245, 158, 11, 0.03); padding: 16px; margin-top: 15px;">
                        <div style="font-size: 13.5px; color: #cbd5e1; line-height: 1.6;">
                            ⚠️ <b>APR Inflation Warning</b>: Your real annualized cost rate is <b>+{diff:.2f}% higher</b> than the advertised {nominal}% p.a. rate.<br>
                            <b>Audit Explainability Rationale</b>: Upfront deductions of {currency}{tot_deductions:,.2f} lower the actual capital in your hands to {currency}{net:,.2f}, 
                            yet your monthly EMIs are calculated on the full face amount of {currency}{p:,.2f}. This upfront capital reduction increases your effective interest yield.
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

    # Compliance Alerts Widget
    from modules.analyzer.compliance import check_regulatory_compliance
    compliance_alerts = check_regulatory_compliance(metrics, charges)
    if compliance_alerts:
        st.markdown(
            """
            <h3 style="margin-top: 30px; margin-bottom: 20px; font-size: 18px; font-family: 'Space Grotesk', sans-serif; font-weight: 700;">⚖️ Regulatory Compliance Alerts</h3>
            """,
            unsafe_allow_html=True
        )
        for alert in compliance_alerts:
            sev = alert["severity"]
            if sev == "CRITICAL":
                glow = "glow-border-rose"
                bg = "rgba(239, 68, 68, 0.03)"
                color = "#ef4444"
                icon = "🚨"
            elif sev == "WARNING":
                glow = "glow-border-amber"
                bg = "rgba(245, 158, 11, 0.02)"
                color = "#f59e0b"
                icon = "⚠️"
            else:
                glow = "glow-border-indigo"
                bg = "rgba(99, 102, 241, 0.02)"
                color = "#6366f1"
                icon = "ℹ️"
                
            st.markdown(
                f"""
                <div class="premium-card {glow}" style="background: {bg}; padding: 18px; margin-bottom: 15px; border-left: 4px solid {color};">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; flex-wrap: wrap; gap: 8px;">
                        <span style="font-weight: 700; color: {color}; font-size: 14px; font-family: 'Space Grotesk', sans-serif;">{icon} {alert['title']}</span>
                        <span style="font-size: 9px; background: rgba(255,255,255,0.04); color: #94a3b8; padding: 2px 8px; border-radius: 4px; font-family: monospace;">{alert['law_reference']}</span>
                    </div>
                    <div style="font-size: 13px; color: #cbd5e1; line-height: 1.5; margin-bottom: 6px;">{alert['description']}</div>
                    <div style="font-size: 12px; color: #94a3b8; font-style: italic;"><b>Impact:</b> {alert['impact']}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

    # Amortization visualizer
    st.markdown(
        """
        <h3 style="margin-top: 30px; margin-bottom: 20px; font-size: 18px; font-family: 'Space Grotesk', sans-serif; font-weight: 700;">📈 Loan Amortization Schedule</h3>
        """,
        unsafe_allow_html=True
    )
    
    schedule = generate_amortization_schedule(
        metrics["loan_amount"],
        metrics["interest_rate_annual"],
        metrics["tenure_months"],
        metrics["emi"]
    )
    
    if schedule:
        df_sched = pd.DataFrame(schedule)
        
        # Plot outstanding balance
        fig_amort = go.Figure()
        fig_amort.add_trace(go.Scatter(
            x=df_sched["Month"],
            y=df_sched["Outstanding Balance"],
            mode='lines',
            name='Outstanding Balance',
            line=dict(color='#06b6d4', width=3),
            fill='tozeroy',
            fillcolor='rgba(6, 182, 212, 0.04)',
            hovertemplate="Month %{x}<br>Balance: ₹%{y:,.2f}<extra></extra>"
        ))
        
        fig_amort.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='#cbd5e1',
            font_family="Plus Jakarta Sans",
            height=260,
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis=dict(
                title="Repayment Month",
                showgrid=False,
                linecolor='rgba(255,255,255,0.08)'
            ),
            yaxis=dict(
                title=f"Outstanding Balance ({currency})",
                showgrid=True,
                gridcolor='rgba(255,255,255,0.04)',
                linecolor='rgba(255,255,255,0.08)'
            )
        )
        st.plotly_chart(fig_amort, use_container_width=True, config={'displayModeBar': False})
        
        # Expander with details table
        with st.expander("🔍 View Month-by-Month Repayment Breakdown Table"):
            df_formatted = df_sched.copy()
            df_formatted["EMI"] = df_formatted["EMI"].map(lambda x: f"₹{x:,.2f}")
            df_formatted["Interest Paid"] = df_formatted["Interest Paid"].map(lambda x: f"₹{x:,.2f}")
            df_formatted["Principal Repaid"] = df_formatted["Principal Repaid"].map(lambda x: f"₹{x:,.2f}")
            df_formatted["Outstanding Balance"] = df_formatted["Outstanding Balance"].map(lambda x: f"₹{x:,.2f}")
            st.dataframe(df_formatted, use_container_width=True, hide_index=True)

    # Row 3: Transparency Score
    st.markdown(
        """
        <h3 style="margin-top: 30px; margin-bottom: 20px; font-size: 18px; font-family: 'Space Grotesk', sans-serif; font-weight: 700;">🛡️ Contract Transparency Score</h3>
        """,
        unsafe_allow_html=True
    )
    
    score = transparency["score"]
    
    # Determine color classification
    if score >= 80:
        score_color = "#10b981" # Green
        verdict = "Consumer Friendly"
        verdict_desc = "This contract is clear, contains standard fees, has low penalty exposure, and provides detailed terms."
    elif score >= 60:
        score_color = "#f59e0b" # Yellow
        verdict = "Moderate Complexity / Caution"
        verdict_desc = "The contract contains several additional fees or charges. Review the prepayment penalties and late charges carefully."
    else:
        score_color = "#f43f5e" # Red
        verdict = "High Risk / Predatory Details"
        verdict_desc = "This document exposes the borrower to high penalty structures, lock-in periods, or missing fee details. Proceed with caution."
        
    col_score, col_breakdown = st.columns([1, 2])
    
    with col_score:
        st.markdown(
            f"""
            <div class="premium-card" style="text-align: center; padding: 25px; min-height: 380px; display: flex; flex-direction: column; justify-content: center; align-items: center; background: rgba(15,23,42,0.4);">
                <span style="font-size: 12px; color: #94a3b8; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;">Transparency Score</span>
            """,
            unsafe_allow_html=True
        )
        
        # Build Gauge Chart
        fig = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = score,
            domain = {'x': [0, 1], 'y': [0, 1]},
            number = {'font': {'color': '#ffffff', 'family': 'Outfit', 'size': 44}},
            gauge = {
                'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#475569", 'tickfont': {'size': 9}},
                'bar': {'color': score_color},
                'bgcolor': "rgba(255,255,255,0.02)",
                'borderwidth': 1,
                'bordercolor': "rgba(255,255,255,0.05)",
                'steps': [
                    {'range': [0, 60], 'color': 'rgba(244, 63, 94, 0.05)'},
                    {'range': [60, 80], 'color': 'rgba(245, 158, 11, 0.05)'},
                    {'range': [80, 100], 'color': 'rgba(16, 185, 129, 0.05)'}
                ],
            }
        ))
        
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font={'color': "#ffffff", 'family': "Plus Jakarta Sans"},
            margin=dict(l=15, r=15, t=10, b=10),
            height=160
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        
        st.markdown(
            f"""
                <div style="background-color: {score_color}1e; border: 1px solid {score_color}33; padding: 6px 14px; border-radius: 20px; font-weight: 700; color: {score_color}; display: inline-block; font-size: 12px; margin-top: 10px; text-transform: uppercase; letter-spacing: 0.02em;">
                    {verdict}
                </div>
                <p style="margin: 15px 0 0 0; font-size: 12px; color: #cbd5e1; line-height: 1.5; text-align: center;">
                    {verdict_desc}
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        
    with col_breakdown:
        st.markdown(
            """
            <div class="premium-card" style="padding: 24px; min-height: 380px; display: flex; flex-direction: column; justify-content: space-between;">
                <h4 style="margin: 0 0 15px 0; color: #ffffff; font-size: 14px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 10px;">Evaluation Breakdown</h4>
            """,
            unsafe_allow_html=True
        )
        tb = transparency["breakdown"]
        
        # Custom HTML score bar helper
        def draw_score_bar(label, value, max_val):
            pct = (value / max_val) * 100
            st.markdown(
                f"""
                <div style="margin-bottom: 15px; width: 100%;">
                    <div style="display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 6px;">
                        <span style="color: #cbd5e1; font-weight: 600;">{label}</span>
                        <span style="color: #94a3b8; font-weight: bold;">{value} / {max_val}</span>
                    </div>
                    <div style="background: rgba(255,255,255,0.04); height: 8px; border-radius: 4px; overflow: hidden; border: 1px solid rgba(255,255,255,0.02); width: 100%;">
                        <div style="background: linear-gradient(90deg, #6366f1 0%, #22d3ee 100%); width: {pct}%; height: 100%; border-radius: 4px;"></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
            
        draw_score_bar("Information Completeness", tb["information_completeness"], 15)
        draw_score_bar("Prepayment & Foreclosure Terms", tb["prepayment_conditions"], 15)
        draw_score_bar("Penalty Exposure", tb["penalty_exposure"], 15)
        draw_score_bar("Fee Clarity", tb["fee_clarity"], 20)
        draw_score_bar("Contract Simplicity", tb["contract_complexity"], 15)
        draw_score_bar("Additional Charges Count", tb["additional_charges"], 20)
        st.markdown("</div>", unsafe_allow_html=True)

    # 3-Category Verification Catalog Section
    st.markdown(
        """
        <h3 style="margin-top: 30px; margin-bottom: 20px; font-size: 18px; font-family: 'Space Grotesk', sans-serif; font-weight: 700;">🛡️ Term Verification & Audit Catalog</h3>
        """,
        unsafe_allow_html=True
    )
    
    # 4 columns grid layout using Streamlit columns
    cat_cols = st.columns(4)
    for idx, term in enumerate(terms_status):
        col_idx = idx % 4
        status = term["status"]
        if status == "VERIFIED":
            glow = "glow-border-emerald"
            badge_bg = "rgba(16, 185, 129, 0.1)"
            badge_txt = "#10b981"
        elif status == "KEYWORD DETECTED":
            glow = "glow-border-amber"
            badge_bg = "rgba(245, 158, 11, 0.1)"
            badge_txt = "#f59e0b"
        else:
            glow = "glow-border-rose"
            badge_bg = "rgba(239, 68, 68, 0.1)"
            badge_txt = "#EF4444"
            
        with cat_cols[col_idx]:
            st.markdown(
                f"""
                <div class="premium-card {glow}" style="padding: 16px; background: rgba(255,255,255,0.015); border: 1px solid rgba(148,163,184,0.1); min-height: 140px; display: flex; flex-direction: column; justify-content: space-between; margin-bottom: 15px;">
                    <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
                        <span style="font-weight: 700; color: #ffffff; font-size: 12px; font-family: 'Space Grotesk', sans-serif;">{term['name']}</span>
                    </div>
                    <div>
                        <div style="font-size: 16px; font-weight: 800; color: #cbd5e1; font-family: 'Outfit', sans-serif; word-break: break-all;">{term['value']}</div>
                        <span style="background: {badge_bg}; color: {badge_txt}; font-size: 8px; font-weight: 800; padding: 2px 6px; border-radius: 4px; text-transform: uppercase; letter-spacing: 0.05em; display: inline-block; margin-top: 6px;">{status}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )


