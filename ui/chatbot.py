import streamlit as st
import requests
from modules.analyzer.compliance import check_regulatory_compliance

def query_ai_chatbot(user_input: str, context_text: str, history: list) -> str:
    """Answers strictly using uploaded loan document context. Returns exact refusal message if missing."""
    REFUSAL_MSG = "This information is not available in the uploaded document"

    if not context_text or "No active document analyzed" in context_text or not context_text.strip():
        return REFUSAL_MSG

    # 1. Try FastAPI endpoint
    try:
        res = requests.post(
            "http://127.0.0.1:8000/api/chat",
            json={
                "message": user_input,
                "context_text": context_text,
                "history": history
            },
            timeout=2.0
        )
        if res.status_code == 200:
            ans = res.json().get("response")
            if ans:
                return ans
    except Exception:
        pass

    # 2. Try direct Ollama LLM Client
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
            f"--- CONTRACT CONTEXT ---\n{context_text}\n-----------------------\n"
        )
        prompt = f"User Question: {user_input}\nRespond in JSON: {{\"response\": \"your clear answer strictly from context or \\\"This information is not available in the uploaded document\\\"\"}}"
        res = client.generate_json(prompt, system_prompt)
        if isinstance(res, dict) and "response" in res:
            ans = res["response"].strip()
            if ans:
                return ans
    except Exception:
        pass

    # 3. Deterministic In-Memory Document QA Engine
    msg = user_input.lower().strip()
    ctx = context_text or ""
    ctx_lower = ctx.lower()

    if any(w in msg for w in ["fee", "hidden", "charge", "cost"]):
        if "extracted charges:" in ctx_lower:
            charges_part = ctx.split("Extracted Charges:")[1].split("Regulatory Warnings:")[0].strip()
            if charges_part and charges_part != "None":
                return f"📋 **Charges Extracted From Your Document:**\n\n{charges_part}"
        lines = [l for l in ctx.split("\n") if any(k in l.lower() for k in ["fee", "charge", "cost"])]
        if lines:
            return "📋 **Fee Details Extracted From Document:**\n\n" + "\n".join(lines)

    if "insurance" in msg:
        if "insurance" in ctx_lower:
            lines = [l for l in ctx.split("\n") if "insurance" in l.lower()]
            if lines:
                return "📋 **Insurance Details In Document:**\n\n" + "\n".join(lines)
        return REFUSAL_MSG

    if any(w in msg for w in ["penalty", "late", "prepay", "foreclos", "bounce"]):
        lines = [l for l in ctx.split("\n") if any(k in l.lower() for k in ["penalty", "late", "prepay", "foreclos", "bounce"])]
        if lines:
            return "🚨 **Penalty Clauses Identified In Document:**\n\n" + "\n".join(lines)

    if any(w in msg for w in ["warning", "alert", "compliance", "rbi", "risk"]):
        if "regulatory warnings:" in ctx_lower:
            alerts_part = ctx.split("Regulatory Warnings:")[1].strip()
            if alerts_part and alerts_part != "None":
                return "⚠️ **Regulatory Compliance Findings From Document:**\n\n" + alerts_part

    if any(w in msg for w in ["interest", "rate", "emi", "tenure", "amount", "sanction", "principal", "lender", "borrower"]):
        summary_lines = [line for line in ctx.split("\n") if any(k in line.lower() for k in ["amount", "interest", "rate", "tenure", "emi", "sanction", "principal", "lender", "borrower"])]
        if summary_lines:
            return "📊 **Primary Financial Terms In Document:**\n\n" + "\n".join(summary_lines)

    # Search for specific phrase match in context
    for line in ctx.split("\n"):
        line_clean = line.strip()
        if line_clean and len(line_clean) > 5 and any(word in line_clean.lower() for word in msg.split() if len(word) > 3 and word in line_clean.lower()):
            return f"ℹ️ **Document Match:**\n\n{line_clean}"

    return REFUSAL_MSG

def render_chatbot_page():
    st.markdown(
        """
        <div style="margin-bottom: 25px;">
            <h1 style="margin: 0; background: linear-gradient(135deg, #ffffff 0%, #a5b4fc 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 32px; font-weight: 800; font-family: 'Space Grotesk', sans-serif;">💬 AI Loan Assistant</h1>
            <p style="margin: 5px 0 0 0; color: #94a3b8; font-size: 14px; line-height: 1.6;">
                Ask specific questions about your uploaded agreement clauses, interest calculations, penalties, or compliance alerts.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Initialize message list in session state
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {"role": "assistant", "content": "Hello! I am your AI Loan Assistant. Ask me any questions directly related to your uploaded loan agreement."}
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
        doc_text = st.session_state.get("document_text", st.session_state.get("raw_text", ""))
        
        # Calculate compliance alerts on the fly
        from modules.analyzer.compliance import check_regulatory_compliance
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

Document Text:
{doc_text}
"""

    # Chat Input bar
    with st.form("chat_form", clear_on_submit=True):
        placeholder = "Ask about late fees, prepayment limits, hidden costs..." if "metrics" in st.session_state and st.session_state.metrics else "Please upload a document to unlock contract-specific Q&A"
        user_input = st.text_input("Your Message", placeholder=placeholder)
        submit_chat = st.form_submit_button("Send Query")
        
        if submit_chat and user_input:
            # Append user message
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            
            # Omit introductory assistant greeting from history payload
            history_payload = st.session_state.chat_history[1:-1]
            
            # Get response using multi-tier fallback query engine
            ans = query_ai_chatbot(user_input, context_text, history_payload)
                
            # Append assistant message
            st.session_state.chat_history.append({"role": "assistant", "content": ans})
            st.rerun()


