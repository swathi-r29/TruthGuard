import streamlit as st
from ui.upload import render_upload_page
from ui.dashboard import render_dashboard_page
from ui.charges import render_charges_page
from ui.evidence import render_evidence_page
from ui.comparison import render_comparison_page
from ui.simulator import render_simulator_page
from ui.report import render_report_page
from ui.chatbot import render_chatbot_page
from ui.negotiation_ui import render_negotiation_page

# Set up Streamlit Page Configuration
st.set_page_config(
    page_title="Debt Detox — AI Debt Cost Auditer",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Define session state variables early
if "doc_name" not in st.session_state:
    st.session_state.doc_name = None
if "metrics" not in st.session_state:
    st.session_state.metrics = None
if "charges" not in st.session_state:
    st.session_state.charges = None
if "transparency" not in st.session_state:
    st.session_state.transparency = None

# Apply Rich Custom CSS/Typography for Premium Dark Financial Intelligence Theme
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');
    
    :root {
        --bg-color: #07111F;
        --bg-gradient: linear-gradient(180deg, #07111F 0%, #0A1628 100%);
        --text-color: #F8FAFC;
        --heading-color: #F8FAFC;
        --secondary-text: #94A3B8;
        --border-color: rgba(148, 163, 184, 0.15);
        --card-bg: #0F1E33;
        --secondary-card-bg: #13253D;
        --sidebar-bg: #0A1628;
        --primary-cyan: #38BDF8;
        --secondary-indigo: #6366F1;
        --savings-green: #10B981;
        --warning-amber: #F59E0B;
        --critical-red: #EF4444;
        --button-bg: linear-gradient(135deg, #6366F1 0%, #38BDF8 100%);
        --button-hover: linear-gradient(135deg, #38BDF8 0%, #6366F1 100%);
        --tab-selected: #38BDF8;
        --radio-label: #F8FAFC;
        --input-label: #F8FAFC;
    }
    
    html, body, [class*="css"], [data-testid="stAppViewContainer"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
        background-color: var(--bg-color) !important;
        color: var(--text-color) !important;
    }
    
    [data-testid="stApp"] {
        background: var(--bg-gradient) !important;
    }
    
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Outfit', sans-serif !important;
        font-weight: 700 !important;
        color: var(--heading-color) !important;
        letter-spacing: -0.02em !important;
    }

    /* Global dynamic override for inline-styled colors in HTML components to support themes */
    div h1[style], div h2[style], div h3[style], div h4[style], div h5[style], div h6[style] {
        color: var(--heading-color) !important;
        background: none !important;
        -webkit-text-fill-color: var(--heading-color) !important;
    }
    
    div[style*="color: #ffffff"], span[style*="color: #ffffff"], p[style*="color: #ffffff"], h3[style*="color: #ffffff"] {
        color: var(--heading-color) !important;
    }
    div[style*="color: #cbd5e1"], span[style*="color: #cbd5e1"], p[style*="color: #cbd5e1"] {
        color: var(--text-color) !important;
    }
    div[style*="color: #94a3b8"], span[style*="color: #94a3b8"], p[style*="color: #94a3b8"] {
        color: var(--secondary-text) !important;
    }
    div[style*="color:#ffffff"], span[style*="color:#ffffff"], p[style*="color:#ffffff"], h3[style*="color:#ffffff"] {
        color: var(--heading-color) !important;
    }
    div[style*="color:#cbd5e1"], span[style*="color:#cbd5e1"], p[style*="color:#cbd5e1"] {
        color: var(--text-color) !important;
    }
    div[style*="color:#94a3b8"], span[style*="color:#94a3b8"], p[style*="color:#94a3b8"] {
        color: var(--secondary-text) !important;
    }
    
    /* Sidebar Custom Glassmorphic Styling */
    [data-testid="stSidebar"] {
        background-color: var(--sidebar-bg) !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        border-right: 1px solid var(--border-color) !important;
    }
    
    /* Streamlit Native Cards Override */
    div[data-testid="stExpander"] {
        background: var(--card-bg) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 16px !important;
        backdrop-filter: blur(8px) !important;
    }
    
    div[data-testid="stExpander"] details {
        border: none !important;
    }
    
    div[data-testid="stExpander"]:hover {
        border-color: var(--tab-selected) !important;
        box-shadow: 0 4px 20px rgba(56, 189, 248, 0.08) !important;
    }
    
    /* Form inputs & buttons customization */
    button[kind="secondaryFormSubmit"], button[kind="primaryFormSubmit"], button[kind="secondary"], button[kind="primary"], button[data-testid="baseButton-secondary"], button[data-testid="baseButton-primary"] {
        background: var(--button-bg) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.5rem 1.5rem !important;
        font-weight: 600 !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.2) !important;
    }
    
    button[kind="secondaryFormSubmit"]:hover, button[kind="primaryFormSubmit"]:hover, button[kind="secondary"]:hover, button[kind="primary"]:hover, button[data-testid="baseButton-secondary"]:hover, button[data-testid="baseButton-primary"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(56, 189, 248, 0.3) !important;
        background: var(--button-hover) !important;
        color: #ffffff !important;
    }

    /* Dark Input & TextArea High Contrast Override */
    div[data-baseweb="textarea"] textarea, div[data-baseweb="input"] input, textarea, input {
        background-color: #0F1E33 !important;
        color: #F8FAFC !important;
        border: 1px solid rgba(148, 163, 184, 0.25) !important;
        border-radius: 8px !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }

    div[data-baseweb="textarea"], div[data-baseweb="input"] {
        background-color: #0F1E33 !important;
        border-radius: 8px !important;
    }
    
    /* Styled Alert/Success/Warning containers */
    .stAlert {
        background: var(--card-bg) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 16px !important;
        color: var(--text-color) !important;
    }
    
    /* Tabs customization */
    .stTabs [data-baseweb="tab-list"] {
        background-color: transparent !important;
        border-bottom: 1px solid var(--border-color) !important;
        gap: 15px !important;
    }
    
    .stTabs [data-baseweb="tab"] {
        color: var(--secondary-text) !important;
        background-color: transparent !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        border: none !important;
        padding: 10px 16px !important;
        transition: all 0.2s ease !important;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        color: var(--heading-color) !important;
    }
    
    .stTabs [aria-selected="true"] {
        color: var(--tab-selected) !important;
        border-bottom: 2px solid var(--tab-selected) !important;
    }
    
    /* Hide default radio circle markers and format sidebar buttons */
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] {
        display: none !important;
    }
    
    [data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] {
        gap: 6px !important;
    }
    
    [data-testid="stSidebar"] [data-testid="stRadio"] label {
        background-color: rgba(255, 255, 255, 0.01) !important;
        border: 1px solid rgba(255, 255, 255, 0.03) !important;
        border-radius: 10px !important;
        padding: 10px 16px !important;
        margin-bottom: 2px !important;
        width: 100% !important;
        cursor: pointer !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        display: flex !important;
        align-items: center !important;
    }
    
    /* Complete hiding of Streamlit radio button markers */
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label [data-testid="stMarker"],
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label div[class*="st-c"],
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label > div:first-child {
        display: none !important;
    }
    
    [data-testid="stSidebar"] [data-testid="stRadio"] label div[data-bv-tabindex],
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] {
        margin-left: 0 !important;
    }
    
    [data-testid="stSidebar"] [data-testid="stRadio"] label p {
        margin: 0 !important;
        color: var(--secondary-text) !important;
        font-weight: 600 !important;
        font-size: 13.5px !important;
    }
    
    [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
        background-color: rgba(56, 189, 248, 0.06) !important;
        border-color: rgba(56, 189, 248, 0.2) !important;
    }
    
    [data-testid="stSidebar"] [data-testid="stRadio"] label:hover p {
        color: var(--text-color) !important;
    }
    
    [data-testid="stSidebar"] [data-testid="stRadio"] div[data-checked="true"] label {
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, rgba(56, 189, 248, 0.15) 100%) !important;
        border: 1px solid rgba(56, 189, 248, 0.4) !important;
        border-left: 4px solid var(--primary-cyan) !important;
        box-shadow: 0 0 12px rgba(56, 189, 248, 0.08) !important;
    }
    
    [data-testid="stSidebar"] [data-testid="stRadio"] div[data-checked="true"] label p {
        color: var(--primary-cyan) !important;
        font-weight: 700 !important;
    }
    
    /* Drag-and-drop file uploader styling */
    [data-testid="stFileUploader"] {
        background-color: var(--card-bg) !important;
        border: 1.5px dashed rgba(56, 189, 248, 0.25) !important;
        border-radius: 16px !important;
        padding: 24px !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15) !important;
    }
    
    [data-testid="stFileUploader"]:hover {
        border-color: var(--primary-cyan) !important;
        background-color: rgba(56, 189, 248, 0.01) !important;
        box-shadow: 0 8px 30px rgba(56, 189, 248, 0.1) !important;
    }
    
    [data-testid="stFileUploader"] section {
        background-color: transparent !important;
        border: none !important;
    }
    
    [data-testid="stFileUploader"] label {
        color: var(--text-color) !important;
        font-weight: 600 !important;
    }
    
    /* Sliders and text fields override */
    div[data-testid="stWidgetLabel"] p {
        color: var(--input-label) !important;
        font-weight: 600 !important;
    }
    
    /* Custom style classes */
    .premium-card {
        background: var(--card-bg) !important;
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid var(--border-color) !important;
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .premium-card:hover {
        transform: translateY(-2px);
        border-color: var(--tab-selected) !important;
        box-shadow: 0 8px 24px rgba(56, 189, 248, 0.1);
    }
    
    .glow-border-indigo { border-left: 4px solid #6366F1 !important; }
    .glow-border-cyan { border-left: 4px solid #38BDF8 !important; }
    .glow-border-rose { border-left: 4px solid #EF4444 !important; }
    .glow-border-amber { border-left: 4px solid #F59E0B !important; }
    .glow-border-emerald { border-left: 4px solid #10B981 !important; }
    
    .gradient-text-indigo-cyan {
        background: linear-gradient(135deg, var(--primary-cyan) 0%, var(--text-color) 100%) !important;
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
    }
    
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, var(--primary-cyan) 0%, var(--secondary-indigo) 100%) !important;
    }
    
    header[data-testid="stHeader"] {
        background-color: rgba(0,0,0,0) !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Sidebar Header & Branding
st.sidebar.markdown(
    """
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 20px; padding: 12px 16px; border-radius: 16px; background: var(--card-bg); border: 1px solid var(--border-color);">
        <span style="font-size: 26px;">🛡️</span>
        <div style="text-align: left;">
            <h2 style="margin: 0; background: linear-gradient(135deg, #38BDF8 0%, #6366F1 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 18px; font-weight: 800; font-family: 'Space Grotesk', sans-serif; letter-spacing: -0.02em; display: inline-block;">DEBT DETOX</h2>
            <div style="margin-top: 1px; color: var(--secondary-text); font-size: 9px; letter-spacing: 0.05em; text-transform: uppercase; font-weight: 700;">AI Debt Cost Auditor</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# Active Document Summary in Sidebar (If processed)
if st.session_state.metrics is not None and st.session_state.get("doc_name") is not None:
    score = st.session_state.transparency["score"]
    audit_status = st.session_state.get("audit_status", "VERIFIED")
    
    if audit_status == "FAILED":
        score_color = "#ef4444"
        risk_label = "Audit Failed"
    elif score >= 80:
        score_color = "#10b981"
        risk_label = "Low Risk"
    elif score >= 60:
        score_color = "#f59e0b"
        risk_label = "Medium Risk"
    else:
        score_color = "#ef4444"
        risk_label = "High Risk"
        
    currency = "₹"
    st.sidebar.markdown(
        f"""
        <div style="background: #0F1E33; border: 1px solid rgba(148,163,184,0.15); border-radius: 16px; padding: 14px; margin-bottom: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.25);">
            <div style="font-size: 8.5px; color: #94A3B8; text-transform: uppercase; font-weight: 800; letter-spacing: 0.08em; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
                <span>Active Loan Profile</span>
                <span style="background: {score_color}1e; color: {score_color}; padding: 2px 6px; border-radius: 4px; font-weight: 800; font-size: 8px;">{audit_status}</span>
            </div>
            <div style="font-weight: 700; color: #F8FAFC; font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-bottom: 8px; font-family: 'Outfit', sans-serif;">📄 {st.session_state.doc_name}</div>
            <div style="font-size: 11px; color: #F8FAFC; border-top: 1px solid rgba(148,163,184,0.12); padding-top: 8px; display: flex; flex-direction: column; gap: 6px;">
                <div style="display: flex; justify-content: space-between;">
                    <span style="color: #94A3B8;">Principal:</span>
                    <span style="font-weight: 600; color: #F8FAFC;">{currency}{st.session_state.metrics['loan_amount']:,.0f}</span>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="color: #94A3B8;">Transparency:</span>
                    <span style="font-weight: 700; color: {score_color};">{score}/100</span>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="color: #94A3B8;">Risk Rating:</span>
                    <span style="background: {score_color}1e; color: {score_color}; border: 1px solid {score_color}33; font-size: 9px; font-weight: 800; padding: 2px 8px; border-radius: 20px; text-transform: uppercase; letter-spacing: 0.02em;">{risk_label}</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
elif st.session_state.get("doc_name") is not None and st.session_state.get("audit_status") == "FAILED":
    score_color = "#ef4444"
    st.sidebar.markdown(
        f"""
        <div style="background: #0F1E33; border: 1px solid rgba(239,68,68,0.25); border-radius: 16px; padding: 14px; margin-bottom: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.25);">
            <div style="font-size: 8.5px; color: #94A3B8; text-transform: uppercase; font-weight: 800; letter-spacing: 0.08em; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
                <span>Active Loan Profile</span>
                <span style="background: rgba(239,68,68,0.1); color: #EF4444; padding: 2px 6px; border-radius: 4px; font-weight: 800; font-size: 8px;">FAILED</span>
            </div>
            <div style="font-weight: 700; color: #F8FAFC; font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-bottom: 8px; font-family: 'Outfit', sans-serif;">📄 {st.session_state.doc_name}</div>
            <div style="font-size: 11px; color: #EF4444; border-top: 1px solid rgba(239,68,68,0.15); padding-top: 8px; font-weight: 600; text-align: center;">
                Analysis Extraction Failed
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
else:
    st.sidebar.markdown(
        """
        <div style="background: #0F1E33; border: 1px dashed rgba(148,163,184,0.15); border-radius: 16px; padding: 14px; margin-bottom: 20px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
            <div style="font-size: 20px; margin-bottom: 4px;">📂</div>
            <div style="font-size: 11px; color: #94A3B8; font-weight: 700; text-transform: uppercase; letter-spacing: 0.02em;">No Active Loan Audited</div>
            <div style="font-size: 9px; color: #6366F1; margin-top: 4px; font-weight: 600;">Upload an agreement to start</div>
        </div>
        """,
        unsafe_allow_html=True
    )

# Sidebar Navigation Selector
menu_options = [
    "📂 Upload & Analyze",
    "📊 Loan Truth Dashboard",
    "💸 Charges & Hidden Costs",
    "🔎 Verification Evidence",
    "📧 Dispute & Negotiation Letter",
    "⚖️ Multi-Debt Strategy",
    "🧮 Payoff Simulator",
    "📋 Download Report",
    "💬 AI Loan Assistant"
]

# Auto-initialize session state on first load if no metrics exist
if st.session_state.metrics is None and "auto_initialized" not in st.session_state:
    st.session_state.auto_initialized = True
    from pathlib import Path
    from ui.upload import run_analysis_pipeline
    sample_path = Path("sample_documents/debt_detox_sample_loan.pdf")
    if not sample_path.exists():
        sample_path = Path("DebtDetox_Validation_Loan_Agreement.pdf")
    if sample_path.exists():
        try:
            with open(sample_path, "rb") as f:
                f_bytes = f.read()
            run_analysis_pipeline(f_bytes, sample_path.name)
        except Exception:
            pass

selected_menu = st.sidebar.radio("Navigation Menu:", menu_options)

# Route Navigation to UI subpages
if selected_menu == "📂 Upload & Analyze":
    render_upload_page()
elif selected_menu == "📊 Loan Truth Dashboard":
    render_dashboard_page()
elif selected_menu == "💸 Charges & Hidden Costs":
    render_charges_page()
elif selected_menu == "🔎 Verification Evidence":
    render_evidence_page()
elif selected_menu == "📧 Dispute & Negotiation Letter":
    render_negotiation_page()
elif selected_menu == "⚖️ Multi-Debt Strategy":
    render_comparison_page()
elif selected_menu == "🧮 Payoff Simulator":
    render_simulator_page()
elif selected_menu == "📋 Download Report":
    render_report_page()
elif selected_menu == "💬 AI Loan Assistant":
    render_chatbot_page()

# Sidebar Footer
st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    <div style="text-align: center; color: var(--secondary-text); font-size: 11px; padding-bottom: 20px;">
        Debt Detox Educational Tool v1.0<br>
        All processing occurs locally.
    </div>
    """,
    unsafe_allow_html=True
)
