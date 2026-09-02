import streamlit as st
import requests
from modules.analyzer.compliance import check_regulatory_compliance

def query_ai_chatbot(user_input: str, context_text: str, history: list) -> str:
    """Tries FastAPI backend first, then direct Ollama LLM, then in-memory financial QA engine."""
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
            "You are Debt Detox AI, an expert consumer finance advisor chatbot. "
            "Help users understand their loan terms, manage debt, and analyze agreement details.\n"
            f"--- CONTRACT CONTEXT ---\n{context_text}\n-----------------------\n"
            "Use context when relevant. Be clear, direct, and encouraging."
        )
        prompt = f"User Question: {user_input}\nRespond in JSON: {{\"response\": \"your clear answer\"}}"
        res = client.generate_json(prompt, system_prompt)
        if isinstance(res, dict) and "response" in res:
            return res["response"]
    except Exception:
        pass

    # 3. Deterministic In-Memory Consumer Finance QA & Contract Advisor Engine
    msg = user_input.lower()
    ctx = context_text or ""

    # General loan management guidance
    if any(w in msg for w in ["manage", "reduce", "payoff", "strategy", "help", "guide", "plan", "how"]):
        resp = "💡 **Debt Detox Strategic Loan Management Plan:**\n\n"
        resp += "1. **Accelerate Repayment**: Pay extra towards principal whenever possible to reduce total interest costs over time.\n"
        resp += "2. **Audit Hidden Fees & Penalties**: Review the **🔎 Verification Evidence** tab for any unverified processing fees, late charges, or foreclosure penalties.\n"
        resp += "3. **Negotiate Disputed Fees**: Use the **📧 Dispute & Negotiation Letter Generator** to request fee waivers or rate re-examinations from your lender.\n"
        resp += "4. **Compare Payoff Strategies**: Use the **⚖️ Multi-Debt Strategy** workspace to test Debt Avalanche (highest interest rate first) or Debt Snowball methods.\n"
        if "Document Name:" in ctx:
            resp += f"\n\n*Contract Context Loaded*: {ctx.split('Document Name:')[1].splitlines()[0].strip()}"
        return resp

    if any(w in msg for w in ["fee", "hidden", "insurance", "charge", "cost"]):
        if "Extracted Charges:" in ctx:
            charges_part = ctx.split("Extracted Charges:")[1].split("Regulatory Warnings:")[0].strip()
            return f"📋 **Charges Extracted From Your Document:**\n\n{charges_part if charges_part else 'No extra hidden fees detected.'}"
        return "No mandatory insurance or extra hidden fees were found in the extracted agreement summary."

    if any(w in msg for w in ["penalty", "late", "prepay", "foreclos", "bounce"]):
        if "Extracted Charges:" in ctx:
            charges_part = ctx.split("Extracted Charges:")[1].split("Regulatory Warnings:")[0].strip()
            penalties = [line for line in charges_part.split("\n") if any(p in line.lower() for p in ["penalty", "late", "bounce", "prepay", "foreclos"])]
            if penalties:
                return "🚨 **Penalty Clauses Identified:**\n\n" + "\n".join(penalties)
        return "No explicit penalty or late payment fee was extracted in the key charges summary."

    if any(w in msg for w in ["warning", "alert", "compliance", "rbi", "risk"]):
        if "Regulatory Warnings:" in ctx:
            alerts_part = ctx.split("Regulatory Warnings:")[1].strip()
            if alerts_part and alerts_part != "None":
                return "⚠️ **Regulatory Compliance Findings:**\n\n" + alerts_part
        return "No critical regulatory compliance warnings were triggered for this agreement."

    if any(w in msg for w in ["interest", "rate", "emi", "tenure", "amount", "sanction"]):
        summary_lines = [line for line in ctx.split("\n") if any(k in line for k in ["Amount", "Interest Rate", "Tenure", "EMI"])]
        return "📊 **Primary Financial Terms:**\n\n" + "\n".join(summary_lines)

    if "No active document analyzed" not in ctx and ctx.strip():
        return f"ℹ️ **Verified Contract Details:**\n\n{ctx.strip()}"

    return "Hello! I am your AI Loan Assistant. Upload a loan document or ask me how to manage your loans, compare repayment strategies, or negotiate fee waivers."

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

