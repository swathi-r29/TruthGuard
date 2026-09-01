import streamlit as st
import requests
from modules.analyzer.compliance import check_regulatory_compliance

def render_chatbot_page():
    st.markdown(
        """
        <div style="margin-bottom: 25px;">
            <h1 style="margin: 0; background: linear-gradient(135deg, #ffffff 0%, #a5b4fc 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 32px; font-weight: 800; font-family: 'Space Grotesk', sans-serif;">💬 AI Loan Assistant</h1>
            <p style="margin: 5px 0 0 0; color: #94a3b8; font-size: 14px; line-height: 1.6;">
                Ask specific questions about your agreement clauses, interest calculations, penalties, or compliance alerts.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Initialize message list in session state
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {"role": "assistant", "content": "Hello! I am your AI Loan Assistant. Ask me any questions about the clauses, terms, or penalties in your uploaded loan agreement."}
        ]

    # Show messages
    for msg in st.session_state.chat_history:
        role = msg["role"]
        icon = "👤" if role == "user" else "🤖"
        bg_col = "rgba(99,102,241,0.03)" if role == "assistant" else "rgba(255,255,255,0.015)"
        border_col = "rgba(99,102,241,0.15)" if role == "assistant" else "rgba(255,255,255,0.05)"
        role_label = "AI Assistant" if role == "assistant" else "You"
        color_label = "#38bdf8" if role == "assistant" else "#c7d2fe"
        
        st.markdown(
            f"""
            <div style="background-color: {bg_col}; border: 1px solid {border_col}; border-radius: 12px; padding: 15px; margin-bottom: 12px;">
                <div style="font-size: 10px; font-weight: 700; color: {color_label}; text-transform: uppercase; margin-bottom: 6px;">
                    {icon} {role_label}
                </div>
                <div style="font-size: 13.5px; color: #ffffff; line-height: 1.5; white-space: pre-wrap;">{msg['content']}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # Compile context if analysis exists
    context_text = "No active document analyzed. Please guide the user to upload their document."
    if "metrics" in st.session_state and st.session_state.metrics is not None:
        metrics = st.session_state.metrics
        charges = st.session_state.charges or []
        doc_name = st.session_state.doc_name
        
        # Calculate compliance alerts on the fly
        alerts = check_regulatory_compliance(metrics, charges)
        
        alerts_str = "\n".join([f"- {a['title']}: {a['description']} [Ref: {a['law_reference']}]" for a in alerts]) if alerts else "None"
        charges_str = "\n".join([f"- {c['canonical_name']}: {c['value']} {c['unit']} ({c['basis']}) [Evidence: {c.get('evidence', '')}]" for c in charges])
        
        context_text = f"""
Document Name: {doc_name}
Sanctioned Amount: ₹{metrics.get('loan_amount')}
Nominal Interest Rate: {metrics.get('interest_rate_annual')}% p.a.
Tenure: {metrics.get('tenure_months')} Months
Stated EMI: ₹{metrics.get('emi')}

Extracted Charges:
{charges_str}

Regulatory Warnings:
{alerts_str}
"""

    # Chat Input bar
    with st.form("chat_form", clear_on_submit=True):
        placeholder = "Ask about late fees, prepayment limits, hidden costs..." if "metrics" in st.session_state and st.session_state.metrics else "Please upload a document to unlock contract-specific Q&A"
        user_input = st.text_input("Your Message", placeholder=placeholder)
        submit_chat = st.form_submit_button("Send Query")
        
        if submit_chat and user_input:
            # Append user message
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            
            # Request backend /api/chat
            try:
                # Omit introductory assistant greeting from history payload
                history_payload = st.session_state.chat_history[1:-1]
                
                res = requests.post(
                    "http://127.0.0.1:8000/api/chat",
                    json={
                        "message": user_input,
                        "context_text": context_text,
                        "history": history_payload
                    }
                )
                if res.status_code == 200:
                    ans = res.json().get("response", "No response from AI server.")
                else:
                    ans = f"Error: Backend returned status code {res.status_code}."
            except Exception as e:
                ans = "Failed to connect to the AI chat engine. Please make sure the FastAPI server is running."
                
            # Append assistant message
            st.session_state.chat_history.append({"role": "assistant", "content": ans})
            st.rerun()
