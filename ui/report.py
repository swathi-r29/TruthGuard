import streamlit as st
from modules.reporting.report_generator import generate_markdown_report

def render_report_page():
    st.markdown(
        """
        <div style="margin-bottom: 25px;">
            <h1 style="margin: 0; background: linear-gradient(135deg, #ffffff 0%, #a5b4fc 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 32px; font-weight: 800; font-family: 'Space Grotesk', sans-serif;">📋 Download Financial Report</h1>
            <p style="margin: 5px 0 0 0; color: #94a3b8; font-size: 14px; line-height: 1.6;">
                Generate a structured, portable Markdown report containing all extracted metrics, transparency scores, fee schedules, and payoff simulations. Keep it for your record or share it with your financial counselor.
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

    metrics = st.session_state.metrics
    charges = st.session_state.charges
    transparency = st.session_state.transparency
    simulation = st.session_state.get("simulation")
    doc_name = st.session_state.doc_name
    currency = "₹"
    
    # 1. Render Loan Health Scorecard at the top
    score = transparency["score"]
    if score >= 80:
        health_color = "#10B981"
        health_label = "LOW RISK / CONSUMER FRIENDLY"
    elif score >= 60:
        health_color = "#F59E0B"
        health_label = "MEDIUM RISK / CAUTION"
    else:
        health_color = "#EF4444"
        health_label = "HIGH RISK / PREDATORY DETAILS"
        
    # Compile key concerns
    concerns = []
    if score < 70:
        concerns.append("Restrictive prepayment/foreclosure conditions or high penalties.")
    unclear_fees = [c for c in charges if c["value"] is None]
    if unclear_fees:
        concerns.append(f"Unspecified fee clauses detected ({len(unclear_fees)} charges mentioned without rates/values).")
    if audit_status == "PARTIAL":
        concerns.append("AI extraction of core loan parameters (principal/rate/tenure) was incomplete.")
    if any(c["classification"] == "PENALTY" for c in charges):
        concerns.append("Late payment or cheque bounce penalty exposure is active.")
        
    if not concerns:
        concerns.append("No critical concerns detected. Contract terms appear standard and transparent.")
        
    concerns_html = "".join([f"<li style='margin-bottom: 5px;'>{c}</li>" for c in concerns])
    
    st.markdown(
        f"""
        <div style="background: #0F1E33; border: 1px solid rgba(148,163,184,0.15); border-radius: 16px; padding: 24px; margin-bottom: 25px; box-shadow: 0 4px 20px rgba(0,0,0,0.25);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; flex-wrap: wrap; gap: 10px;">
                <div>
                    <span style="font-size: 10px; color: #94A3B8; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em;">Loan Audit Evaluation</span>
                    <h2 style="margin: 5px 0 0 0; color: #F8FAFC; font-family: 'Space Grotesk', sans-serif; font-weight: 800; font-size: 20px;">LOAN HEALTH SCORE</h2>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 28px; font-weight: 800; color: {health_color}; font-family: 'Outfit', sans-serif;">{score} <span style="font-size: 14px; color: #94A3B8; font-weight: 500;">/ 100</span></div>
                    <span style="background: {health_color}1e; color: {health_color}; border: 1px solid {health_color}33; font-size: 8px; font-weight: 800; padding: 2px 10px; border-radius: 20px; text-transform: uppercase; letter-spacing: 0.05em; display: inline-block; margin-top: 4px;">{health_label}</span>
                </div>
            </div>
            <div style="border-top: 1px solid rgba(148,163,184,0.15); padding-top: 15px;">
                <div style="font-size: 11px; color: #F8FAFC; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;">Main concerns:</div>
                <ul style="margin: 0; padding-left: 20px; font-size: 13px; color: #94A3B8; line-height: 1.6;">
                    {concerns_html}
                </ul>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Compile dynamic action recommendations categorized
    classified_recs = []
    
    # 1. Transparency Score
    if score < 60:
        classified_recs.append({
            "category": "HIGH PRIORITY",
            "title": "Unclear Legalese & Low Contract Transparency",
            "description": f"The loan agreement score is {score}/100, which falls below transparent consumer thresholds. This is driven by missing fee disclosures or excessive penalty clauses.",
            "action": "Request a complete, consolidated written tariff sheet from the lender's credit department before signing."
        })
    elif score < 80:
        classified_recs.append({
            "category": "WARNING",
            "title": "Restrictive Penalty exposure",
            "description": "The agreement has moderate complexity, containing multiple conditional clauses and penalty structures.",
            "action": "Review the specific late payment and Cheque bounce charge schedules in detail."
        })
    else:
        classified_recs.append({
            "category": "INFORMATION",
            "title": "Good Contract Transparency",
            "description": "All core parameters are explicitly detailed and supported by textual references.",
            "action": "Proceed with standard verification steps."
        })
        
    # 2. Unspecified Charges
    if unclear_fees:
        fee_names = ", ".join([c.get("original_name") or c["canonical_name"].replace("_", " ").title() for c in unclear_fees])
        classified_recs.append({
            "category": "HIGH PRIORITY",
            "title": "Clarify Unspecified Fees Mentioned in Text",
            "description": f"The contract text references the following charge clauses but does not disclose their values: {fee_names}.",
            "action": "Obtain written clarification from the lender specifying the exact values of these line items."
        })
        
    # 3. Prepayment caution
    has_foreclosure = any(c["canonical_name"] == "foreclosure_charge" for c in charges)
    if has_foreclosure:
        classified_recs.append({
            "category": "WARNING",
            "title": "Prepayment Foreclosure Penalties Active",
            "description": "A fee is applied if you foreclose the loan early or pay extra principal offsets.",
            "action": "Verify if the total interest saved exceeds the foreclosure penalty fee before initiating any early payoff."
        })
    else:
        classified_recs.append({
            "category": "INFORMATION",
            "title": "No Early Foreclosure Penalties Detected",
            "description": "No foreclosure charges were found, giving you the flexibility to prepay anytime.",
            "action": "Consider setting up prepayments to close the loan faster."
        })
        
    # 4. Late payment
    has_late = any(c["canonical_name"] == "late_payment_fee" for c in charges)
    if has_late:
        classified_recs.append({
            "category": "WARNING",
            "title": "Late Payment Delinquency Penalty Clauses Active",
            "description": "Lender charges penalty interest or flat fees if EMIs are delayed.",
            "action": "Configure direct auto-debit transfers to avoid late penalties."
        })
        
    # 5. Payoff acceleration
    if simulation and simulation.get("success") and simulation.get("months_saved", 0) > 0:
        classified_recs.append({
            "category": "OPPORTUNITY",
            "title": "Repayment Acceleration Opportunity Available",
            "description": f"Prepaying an extra monthly budget of ₹{st.session_state.get('simulation_extra_monthly', 1000.0):,.2f} is simulated to save you ₹{simulation['interest_saved']:,.2f} and compress tenure by {simulation['months_saved']} months.",
            "action": f"Initiate monthly surplus payments to capture these simulated interest savings."
        })

    # Render recommendations as priority action cards
    st.markdown(
        """
        <h4 style="margin-top: 25px; margin-bottom: 15px; font-size: 15px; font-family: 'Space Grotesk', sans-serif; font-weight: 700; color: #ffffff;">📋 Key Recommendations & Action Items</h4>
        """,
        unsafe_allow_html=True
    )
    
    for rec in classified_recs:
        cat = rec["category"]
        if cat == "HIGH PRIORITY":
            badge_color = "#EF4444"
            glow_class = "glow-border-rose"
            bg = "rgba(239, 68, 68, 0.015)"
        elif cat == "WARNING":
            badge_color = "#F59E0B"
            glow_class = "glow-border-amber"
            bg = "rgba(245, 158, 11, 0.015)"
        elif cat == "OPPORTUNITY":
            badge_color = "#38BDF8"
            glow_class = "glow-border-cyan"
            bg = "rgba(56, 189, 248, 0.015)"
        else:
            badge_color = "#6366F1"
            glow_class = "glow-border-indigo"
            bg = "rgba(99, 102, 241, 0.015)"
            
        st.markdown(
            f"""
            <div class="premium-card {glow_class}" style="padding: 20px; margin-bottom: 15px; background: {bg}; border: 1px solid rgba(148,163,184,0.12);">
                <div style="font-size: 10px; color: {badge_color}; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 6px;">{cat}</div>
                <h4 style="margin: 0 0 10px 0; font-size: 14px; font-weight: 700; color: #ffffff; font-family: 'Space Grotesk', sans-serif;">{rec['title']}</h4>
                <p style="color: #cbd5e1; font-size: 12px; line-height: 1.5; margin-bottom: 12px;">
                    {rec['description']}
                </p>
                <div style="font-size: 11px; color: {badge_color}; font-weight: 700; border-top: 1px solid rgba(148,163,184,0.08); padding-top: 10px; margin-top: 10px;">
                    👉 Recommended Action:<br>
                    <span style="color: #cbd5e1; font-weight: 500; font-family: 'Plus Jakarta Sans', sans-serif; font-size: 12px; display: inline-block; margin-top: 4px;">{rec['action']}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # Compile list of rec text for markdown generator
    recommendations = [f"{r['category']}: {r['title']} - {r['description']} -> Action: {r['action']}" for r in classified_recs]

    # Generate Markdown String
    report_md = generate_markdown_report(
        metrics=metrics,
        charges=charges,
        transparency=transparency,
        simulation=simulation,
        recommendations=recommendations
    )

    st.write("<div style='height: 15px;'></div>", unsafe_allow_html=True)

    # Download Button
    file_base = doc_name.rsplit(".", 1)[0]
    st.download_button(
        label="📥 Download Markdown Report",
        data=report_md,
        file_name=f"debt_detox_report_{file_base}.md",
        mime="text/markdown"
    )

    st.markdown("---")
    st.markdown(
        """
        <h4 style="margin-top: 15px; margin-bottom: 15px; font-size: 16px; font-family: 'Space Grotesk', sans-serif; font-weight: 700; color: #ffffff;">👀 Report Preview</h4>
        """,
        unsafe_allow_html=True
    )
    
    # Styled scrolling viewport for document preview
    st.markdown(
        f"""
        <div class="premium-card" style="padding: 24px; max-height: 420px; overflow-y: auto; background-color: rgba(0, 0, 0, 0.25); border: 1px solid rgba(255,255,255,0.06); font-family: 'Plus Jakarta Sans', sans-serif; font-size: 13px; line-height: 1.6; color: #cbd5e1; white-space: pre-wrap;">{report_md}</div>
        """,
        unsafe_allow_html=True
    )
