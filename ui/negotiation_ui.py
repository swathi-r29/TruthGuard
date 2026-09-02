"""
Streamlit UI Component for Dispute & Negotiation Letter Generator.
"""

import streamlit as st
from modules.active_loan import get_active_loan
from modules.explanation.negotiation import generate_dispute_letter

def render_negotiation_page():
    st.markdown(
        """
        <div style="margin-bottom: 25px;">
            <h1 style="margin: 0; background: linear-gradient(135deg, #ffffff 0%, #38bdf8 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 32px; font-weight: 800; font-family: 'Space Grotesk', sans-serif;">📧 Dispute & Negotiation Letter Generator</h1>
            <p style="margin: 5px 0 0 0; color: #94a3b8; font-size: 14px; line-height: 1.6;">
                Generate an automated, legally-grounded fee waiver & contract renegotiation letter based on extracted loan terms and compliance findings.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    active_loan = get_active_loan(st.session_state)
    if not active_loan or not active_loan.get("metrics"):
        st.markdown(
            """
            <div class="premium-card glow-border-amber" style="background: rgba(245, 158, 11, 0.03); padding: 20px;">
                <div style="font-weight: 700; color: #f59e0b; font-size: 14px; margin-bottom: 5px;">⚠️ No Active Loan Analyzed</div>
                <div style="color: #cbd5e1; font-size: 12px;">Please process a loan document in <b>Upload & Analyze</b> or use <b>Instant Demo Mode</b> to generate a negotiation letter.</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        return

    charges = active_loan.get("charges", [])
    doc_name = active_loan.get("doc_name", "Loan Agreement")

    col_config, col_preview = st.columns([1, 1.2], gap="large")

    with col_config:
        st.markdown("<h3 style='font-size: 18px; color: #38bdf8;'>1. Customize Letter Parameters</h3>", unsafe_allow_html=True)
        
        borrower_name = st.text_input("Borrower Full Name:", value="John Doe", help="Name to appear on the official dispute letter.")
        
        st.markdown("<div style='margin-top: 15px; font-weight: 600; color: #cbd5e1; font-size: 13px;'>Select Disputed Charges to Include:</div>", unsafe_allow_html=True)
        
        selected_canonical_names = []
        if charges:
            for c in charges:
                c_name = c.get("canonical_name", "")
                disp_name = c_name.replace("_", " ").title()
                val = c.get("value")
                unit = c.get("unit", "")
                val_str = f"₹{val:,.2f}" if isinstance(val, (int, float)) and unit != "percent" else f"{val}%"
                
                checked = st.checkbox(f"{disp_name} ({val_str})", value=True, key=f"neg_chk_{c_name}")
                if checked:
                    selected_canonical_names.append(c_name)
        else:
            st.info("No specific fee charges detected to toggle. Standard clause review will be requested.")

        custom_notes = st.text_area("Additional Notes / Specific Requests:", placeholder="e.g., I have maintained a salary account with your bank for 5 years and request an executive relationship waiver.")

    # Generate letter text
    letter_text = generate_dispute_letter(
        active_loan=active_loan,
        selected_charges=selected_canonical_names,
        borrower_name=borrower_name,
        custom_notes=custom_notes
    )

    with col_preview:
        st.markdown("<h3 style='font-size: 18px; color: #10b981;'>2. Generated Formal Notice Preview</h3>", unsafe_allow_html=True)
        
        # High-contrast dark document viewer
        st.markdown(
            f"""<div style="background: #07111F; border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 12px; padding: 20px; max-height: 460px; overflow-y: auto; font-family: monospace; font-size: 12.5px; line-height: 1.6; color: #F8FAFC; white-space: pre-wrap; margin-bottom: 15px; box-shadow: inset 0 2px 10px rgba(0,0,0,0.5);">{letter_text}</div>""",
            unsafe_allow_html=True
        )

        col_b1, col_b2 = st.columns([1, 1])
        with col_b1:
            st.download_button(
                label="📥 Download Notice (.txt)",
                data=letter_text,
                file_name=f"Dispute_Notice_{doc_name.replace(' ', '_')}.txt",
                mime="text/plain",
                use_container_width=True
            )
        with col_b2:
            st.info("💡 Copy the text above and send it via registered email to your lender's grievance desk.")
