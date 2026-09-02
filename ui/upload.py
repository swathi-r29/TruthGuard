import streamlit as st
import os
from pathlib import Path
import config
from modules.document_processor import process_document
from modules.ai_extraction import DocumentExtractor
from modules.charge_detection import detect_charges
from modules.financial_engine import calculate_real_cost_metrics
from modules.analyzer import calculate_transparency_score, calculate_effective_rates
from modules.explanation.explainer import get_simple_explanation, generate_math_example
from modules.ai_extraction.client import OllamaConnectionError, OllamaModelNotFoundError
import textwrap
from modules.active_loan import set_active_loan, get_active_loan

def render_upload_page():
    st.markdown(
        """
        <div style="text-align: center; padding: 40px 20px 20px 20px; background: radial-gradient(circle at 50% 0%, rgba(99, 102, 241, 0.08) 0%, rgba(7, 17, 31, 0) 70%); border-radius: 16px; border: 1px solid rgba(148, 163, 184, 0.08); margin-bottom: 35px; box-shadow: 0 8px 32px rgba(0,0,0,0.3);">
            <div style="font-size: 40px; margin-bottom: 15px;">🛡️</div>
            <h1 style="margin: 0; background: linear-gradient(135deg, #F8FAFC 0%, #38BDF8 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 36px; font-weight: 800; font-family: 'Space Grotesk', sans-serif; letter-spacing: -0.03em;">Know What Your Loan REALLY Costs</h1>
            <p style="margin: 15px auto 0 auto; color: #94A3B8; font-size: 14px; line-height: 1.6; max-width: 680px; font-family: 'Plus Jakarta Sans', sans-serif;">
                Upload your loan agreement and let AI identify verified terms, hidden charges, risky conditions, and repayment opportunities.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Check AI Engine connection status
    try:
        extractor = DocumentExtractor()
        llm_ok = extractor.client.check_connection()
        model_name = extractor.client.model
        model_ok = extractor.client.check_model_available() if llm_ok else False
    except Exception:
        llm_ok = False
        model_name = "unknown"
        model_ok = False

    # Show LLM Status based on the selected provider
    llm_provider = config.LLM_PROVIDER
    if llm_provider == "gemini":
        if not llm_ok:
            st.markdown(
                """
                <div class="premium-card glow-border-cyan" style="padding: 12px 18px; background: rgba(56, 189, 248, 0.02); display: flex; align-items: center; gap: 12px; margin-bottom: 20px;">
                    <div style="color: #38bdf8; font-size: 20px; font-weight: bold;">⚡</div>
                    <div>
                        <div style="font-weight: 700; color: #ffffff; font-size: 13px;">Local Rule & Regex AI Engine Active</div>
                        <div style="color: #94a3b8; font-size: 11px; margin-top: 1px;">No cloud Gemini key set in <code>.env</code>. Running locally with high-precision rule & regex extraction.</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"""
                <div class="premium-card glow-border-emerald" style="padding: 12px 18px; background: rgba(16, 185, 129, 0.02); display: flex; align-items: center; gap: 12px; margin-bottom: 20px;">
                    <div style="color: #10b981; font-size: 20px; font-weight: bold;">✓</div>
                    <div>
                        <div style="font-weight: 700; color: #ffffff; font-size: 13px;">Gemini AI Engine Online</div>
                        <div style="color: #94a3b8; font-size: 11px; margin-top: 1px;">Model: <code>{model_name}</code></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
    else:
        if not llm_ok:
            st.markdown(
                """
                <div class="premium-card glow-border-rose" style="padding: 20px; background: rgba(244, 63, 94, 0.03);">
                    <div style="font-weight: 700; color: #f43f5e; font-size: 14px; margin-bottom: 8px;">⚠️ Local AI Engine (Ollama) is Offline</div>
                    <div style="color: #cbd5e1; font-size: 12px; line-height: 1.5;">
                        Debt Detox runs terms extraction locally for privacy. Please follow these steps to start it:<br>
                        1. Download and run <b>Ollama</b> from <a href="https://ollama.com" target="_blank" style="color: #818cf8; text-decoration: underline;">ollama.com</a>.<br>
                        2. Run <code>ollama pull gemma2:2b</code> in your terminal.<br>
                        3. Make sure Ollama is running at <code>http://localhost:11434</code>.
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        elif not model_ok:
            st.markdown(
                f"""
                <div class="premium-card glow-border-amber" style="padding: 20px; background: rgba(245, 158, 11, 0.03);">
                    <div style="font-weight: 700; color: #f59e0b; font-size: 14px; margin-bottom: 8px;">⚠️ Model '{model_name}' Not Found</div>
                    <div style="color: #cbd5e1; font-size: 12px; line-height: 1.5;">
                        Ollama is online, but the model <code>{model_name}</code> is not installed.<br>
                        Please run <code>ollama pull {model_name}</code> in your command prompt to download it.
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"""
                <div class="premium-card glow-border-emerald" style="padding: 12px 18px; background: rgba(16, 185, 129, 0.02); display: flex; align-items: center; gap: 12px; margin-bottom: 20px;">
                    <div style="color: #10b981; font-size: 20px; font-weight: bold;">✓</div>
                    <div>
                        <div style="font-weight: 700; color: #ffffff; font-size: 13px;">Local AI Engine Online</div>
                        <div style="color: #94a3b8; font-size: 11px; margin-top: 1px;">Model: <code>{model_name}</code></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

    # Instant Demo Mode Cards
    demo_html = """
<div style="background: rgba(56, 189, 248, 0.04); border: 1px solid rgba(56, 189, 248, 0.2); border-radius: 12px; padding: 18px; margin-bottom: 20px;">
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
        <div style="font-weight: 700; color: #38bdf8; font-size: 15px; font-family: 'Space Grotesk', sans-serif;">
            ⚡ Instant Demo Mode (1-Click Presentation Audit)
        </div>
        <span style="background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: 800; text-transform: uppercase;">Reviewer Fast-Path</span>
    </div>
    <div style="color: #94a3b8; font-size: 12px; margin-bottom: 12px;">
        Click any case study below to instantly run the deterministic audit pipeline on sample PDF contracts without waiting on local LLM execution.
    </div>
</div>
"""
    st.markdown(textwrap.dedent(demo_html).strip(), unsafe_allow_html=True)

    demo_col1, demo_col2, demo_col3, demo_col4 = st.columns(4)
    file_bytes = None
    file_name = None

    with demo_col1:
        if st.button("🏢 Apex Personal Loan\n(₹3L @ 14.5%)", use_container_width=True):
            s_path = Path("sample_documents/apex_personal_loan_agreement.pdf")
            if s_path.exists():
                with open(s_path, "rb") as f:
                    file_bytes = f.read()
                file_name = s_path.name

    with demo_col2:
        if st.button("💳 Nova Credit Card\n(42% APR Terms)", use_container_width=True):
            s_path = Path("sample_documents/nova_credit_card_terms.pdf")
            if s_path.exists():
                with open(s_path, "rb") as f:
                    file_bytes = f.read()
                file_name = s_path.name

    with demo_col3:
        if st.button("🛒 SplitPay BNPL\n(Zero-Interest Promo)", use_container_width=True):
            s_path = Path("sample_documents/splitpay_bnpl_contract.pdf")
            if s_path.exists():
                with open(s_path, "rb") as f:
                    file_bytes = f.read()
                file_name = s_path.name

    with demo_col4:
        if st.button("📄 Scanned Micro Loan\n(OCR Fallback)", use_container_width=True):
            s_path = Path("sample_documents/scanned_micro_loan_agreement.pdf")
            if not s_path.exists():
                s_path = Path("DebtDetox_Validation_Loan_Agreement.pdf")
            if s_path.exists():
                with open(s_path, "rb") as f:
                    file_bytes = f.read()
                file_name = s_path.name

    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    # File selection source
    source = st.radio("Or Select Custom Input Method:", ["Upload a New File", "Select from All Sample Files"])

    if source == "Select from All Sample Files":
        sample_dir = Path("sample_documents")
        if sample_dir.exists():
            samples = [f for f in os.listdir(sample_dir) if f.endswith(".pdf")]
            if samples:
                selected_sample = st.selectbox("Select a sample document to analyze:", samples)
                sample_path = sample_dir / selected_sample
                if st.button("Analyze Selected File"):
                    with open(sample_path, "rb") as f:
                        file_bytes = f.read()
                    file_name = selected_sample
            else:
                st.warning("No sample PDF files found in `sample_documents`.")
        else:
            st.warning("Sample documents folder not found.")
            
    else:
        uploaded_file = st.file_uploader("Choose a PDF or Image file", type=["pdf", "png", "jpg", "jpeg"])
        if uploaded_file is not None:
            if st.button("Start AI Analysis"):
                file_bytes = uploaded_file.read()
                file_name = uploaded_file.name

    if file_bytes and file_name:
        run_analysis_pipeline(file_bytes, file_name)

def run_analysis_pipeline(file_bytes: bytes, file_name: str):
    status_container = st.empty()
    
    def render_pipeline_status(step_num, failed_at_step=None, partial_at_step=None):
        steps = [
            "Document Uploaded",
            "Extracting Text",
            "OCR Processing",
            "AI Financial Analysis",
            "Calculating True Cost",
            "Generating Transparency Score"
        ]
        
        html = "<div class='premium-card glow-border-cyan' style='padding: 24px; background: #0F1E33; border: 1px solid rgba(148,163,184,0.15);'>"
        html += "<h3 style='margin-top:0; margin-bottom: 20px; font-size: 15px; color: #ffffff; font-family: \"Space Grotesk\", sans-serif; text-transform: uppercase; letter-spacing: 0.05em;'>⚙️ Analysis Execution Pipeline</h3>"
        
        for idx, name in enumerate(steps):
            num = idx + 1
            is_failed = (failed_at_step == num)
            is_partial = (partial_at_step == num)
            is_completed = (num < step_num) and (not failed_at_step or num < failed_at_step)
            is_active = (num == step_num) and not failed_at_step
            
            if is_failed:
                badge = "<span style='background-color: rgba(239, 68, 68, 0.15); color: #ef4444; border: 1px solid rgba(239,68,68,0.3); border-radius: 50%; width: 22px; height: 22px; display: inline-flex; align-items: center; justify-content: center; font-size: 11px; margin-right: 12px; font-weight: bold;'>✗</span>"
                text_style = "color: #ef4444; font-weight: 600;"
                border_style = "border-left: 3.5px solid #ef4444; box-shadow: 0 0 15px rgba(239,68,68,0.15);"
            elif is_partial:
                badge = "<span style='background-color: rgba(245, 158, 11, 0.15); color: #f59e0b; border: 1px solid rgba(245,158,11,0.3); border-radius: 50%; width: 22px; height: 22px; display: inline-flex; align-items: center; justify-content: center; font-size: 11px; margin-right: 12px; font-weight: bold;'>!</span>"
                text_style = "color: #f59e0b; font-weight: 600;"
                border_style = "border-left: 3.5px solid #f59e0b;"
            elif is_completed:
                badge = "<span style='background-color: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16,185,129,0.3); border-radius: 50%; width: 22px; height: 22px; display: inline-flex; align-items: center; justify-content: center; font-size: 11px; margin-right: 12px; font-weight: bold;'>✓</span>"
                text_style = "color: #cbd5e1;"
                border_style = "border-left: 3.5px solid #10b981;"
            elif is_active:
                badge = "<span style='background-color: rgba(56, 189, 248, 0.2); color: #38bdf8; border: 1px solid rgba(56,189,248,0.5); border-radius: 50%; width: 22px; height: 22px; display: inline-flex; align-items: center; justify-content: center; font-size: 11px; margin-right: 12px; font-weight: bold; animation: pulse_cyan 1.5s infinite;'>●</span>"
                text_style = "color: #ffffff; font-weight: 600;"
                border_style = "border-left: 3.5px solid #38bdf8; box-shadow: 0 0 15px rgba(56,189,248,0.15);"
            else:
                badge = f"<span style='background-color: rgba(255, 255, 255, 0.03); color: #94a3b8; border: 1px solid rgba(255,255,255,0.06); border-radius: 50%; width: 22px; height: 22px; display: inline-flex; align-items: center; justify-content: center; font-size: 10px; margin-right: 12px; font-weight: bold;'>{num}</span>"
                text_style = "color: #475569;"
                border_style = "border-left: 3.5px solid rgba(255,255,255,0.03);"
                
            html += f"""
            <div style='display: flex; align-items: center; padding: 12px 18px; margin-bottom: 10px; border-radius: 8px; {border_style} background: rgba(255,255,255,0.015); border: 1px solid rgba(148,163,184,0.08);'>
                {badge}
                <span style='{text_style} font-size: 13.5px;'>{name}</span>
            </div>
            """
        html += "</div>"
        
        status_container.markdown(
            f"""
            <style>
            @keyframes pulse_cyan {{
                0% {{ box-shadow: 0 0 0 0 rgba(56, 189, 248, 0.4); }}
                70% {{ box-shadow: 0 0 0 6px rgba(56, 189, 248, 0); }}
                100% {{ box-shadow: 0 0 0 0 rgba(56, 189, 248, 0); }}
            }}
            </style>
            {html}
            """,
            unsafe_allow_html=True
        )

    try:
        # Step 1: Document Uploaded
        render_pipeline_status(1)
        doc_result = process_document(file_bytes, file_name)
        if not doc_result.get("success"):
            render_pipeline_status(1, failed_at_step=1)
            st.error(f"Failed to process document: {doc_result.get('error')}")
            st.session_state.audit_status = "FAILED"
            st.session_state.doc_name = file_name
            return
            
        pages = doc_result["pages"]
        total_pages = doc_result["total_pages"]
        ocr_used = doc_result["ocr_used"]
        
        # Step 2: Extracting Text
        render_pipeline_status(2)
        try:
            extractor = DocumentExtractor()
            extracted = extractor.extract_from_pages(pages)
        except Exception as e:
            render_pipeline_status(2, failed_at_step=2)
            st.error(f"Failed to extract document text: {str(e)}")
            st.session_state.audit_status = "FAILED"
            st.session_state.doc_name = file_name
            return
        
        # Step 3: OCR Processing
        render_pipeline_status(3)
        try:
            charges = detect_charges(extracted, pages)
        except Exception as e:
            render_pipeline_status(3, failed_at_step=3)
            st.error(f"Failed to process OCR/charges mapping: {str(e)}")
            st.session_state.audit_status = "FAILED"
            st.session_state.doc_name = file_name
            return
        
        # Step 4: AI Financial Analysis
        render_pipeline_status(4)
        try:
            # Parse extracted values directly without hardcoded defaults
            principal = float(extracted.loan_amount.value) if (extracted.loan_amount and extracted.loan_amount.value is not None) else 0.0
            rate = float(extracted.interest_rate.value) if (extracted.interest_rate and extracted.interest_rate.value is not None) else None
            tenure = int(extracted.tenure.value) if (extracted.tenure and extracted.tenure.value is not None) else 0
            emi = float(extracted.emi.value) if (extracted.emi and extracted.emi.value is not None) else 0.0
            interest_type = (extracted.interest_type.value if extracted.interest_type else None) or "reducing_balance"
            outstanding = float(extracted.outstanding_principal.value) if (hasattr(extracted, 'outstanding_principal') and extracted.outstanding_principal and extracted.outstanding_principal.value is not None) else None
            
            metrics = calculate_real_cost_metrics(
                principal=principal,
                interest_rate_annual=rate if rate is not None else 0.0,
                tenure_months=tenure,
                charges=charges,
                interest_type=interest_type,
                override_emi=emi if emi > 0 else None,
                tax_rate_percent=18.0,
                outstanding_principal=outstanding
            )
        except Exception as e:
            render_pipeline_status(4, failed_at_step=4)
            st.error(f"Failed during financial terms calculations: {str(e)}")
            st.session_state.audit_status = "FAILED"
            st.session_state.doc_name = file_name
            return
            
        # Step 5: Calculating True Cost
        render_pipeline_status(5)
        try:
            if metrics and metrics.get("net_disbursed_amount", 0) > 0 and metrics.get("emi", 0) > 0:
                effective_rates = calculate_effective_rates(
                    net_disbursed=metrics["net_disbursed_amount"],
                    emi=metrics["emi"],
                    tenure_months=metrics["tenure_months"]
                )
                transparency = calculate_transparency_score(metrics, charges, total_pages)
            else:
                effective_rates = None
                transparency = calculate_transparency_score({}, charges, total_pages)
        except Exception as e:
            render_pipeline_status(5, failed_at_step=5)
            st.error(f"Failed to calculate true cost metrics: {str(e)}")
            st.session_state.audit_status = "FAILED"
            st.session_state.doc_name = file_name
            return
        
        # Step 6: Generating Transparency Score
        render_pipeline_status(6)
        try:
            explanations = {}
            math_examples = {}
            for c in charges:
                canonical_name = c["canonical_name"]
                evidence = c["evidence"]
                val = c["value"]
                unit = c["unit"]
                basis = c["basis"]
                
                explanations[canonical_name] = get_simple_explanation(canonical_name, evidence)
                if val is not None:
                    math_examples[canonical_name] = generate_math_example(canonical_name, val, unit, basis)
        except Exception as e:
            render_pipeline_status(6, failed_at_step=6)
            st.error(f"Failed to build transparency results: {str(e)}")
            st.session_state.audit_status = "FAILED"
            st.session_state.doc_name = file_name
            return
            
        status_container.empty()
        
        # Determine overall audit status
        has_principal = (principal > 0.0)
        has_rate = (rate is not None and rate >= 0.0)
        has_tenure = (tenure > 0)
        
        if not has_principal and not has_rate and not has_tenure:
            audit_status = "FAILED"
            data_source_badge = "DATA SOURCE: EXTRACTION FAILED"
        elif not has_principal or not has_rate or not has_tenure:
            audit_status = "PARTIAL"
            data_source_badge = "DATA SOURCE: CURRENT UPLOADED DOCUMENT (PARTIAL)"
        else:
            audit_status = "VERIFIED"
            data_source_badge = "DATA SOURCE: CURRENT UPLOADED DOCUMENT"
            
        # Reset and save fresh ACTIVE_LOAN single source of truth state
        set_active_loan(
            st_session=st.session_state,
            doc_name=file_name,
            doc_type=doc_result.get("file_type", ""),
            total_pages=total_pages,
            ocr_used=ocr_used,
            extracted=extracted,
            charges=charges,
            metrics=metrics,
            effective_rates=effective_rates,
            transparency=transparency,
            explanations=explanations,
            math_examples=math_examples,
            audit_status=audit_status,
            data_source_badge=data_source_badge
        )
        st.session_state.debts_list = []  # Clear previous debt inventory
        
        # Success message with quick instructions
        st.balloons()
        
        status_badge_color = "#10b981" if audit_status == "VERIFIED" else "#f59e0b"
        st.markdown(
            f"""
            <div class="premium-card glow-border-emerald" style="background: rgba(16, 185, 129, 0.02); margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <div style="font-weight: 700; color: #10b981; font-size: 16px;">🎉 Analysis Complete!</div>
                    <span style="background-color: {status_badge_color}1a; color: {status_badge_color}; border: 1px solid {status_badge_color}33; font-size: 10px; padding: 2px 10px; border-radius: 12px; font-weight: 800; letter-spacing: 0.05em; text-transform: uppercase;">{audit_status}</span>
                </div>
                <div style="color: #cbd5e1; font-size: 13px; line-height: 1.5;">
                    Successfully analyzed <b>{file_name}</b>.<br>
                    Please navigate to the <b>Loan Truth Dashboard</b> or <b>Charges & Hidden Costs</b> tab in the sidebar menu to view your detailed audit.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        
    except Exception as e:
        st.session_state.audit_status = "FAILED"
        st.session_state.doc_name = file_name
        status_container.empty()
        st.error(f"An unexpected error occurred during pipeline execution: {str(e)}")
        import traceback
        st.code(traceback.format_exc())

