import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

def render_charges_page():
    st.markdown(
        """
        <div style="margin-bottom: 25px;">
            <h1 style="margin: 0; background: linear-gradient(135deg, #ffffff 0%, #a5b4fc 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 32px; font-weight: 800; font-family: 'Space Grotesk', sans-serif;">💸 Detected Charges & Hidden Costs</h1>
            <p style="margin: 5px 0 0 0; color: #94a3b8; font-size: 14px; line-height: 1.6;">
                Lenders often distribute fees into different categories and page clauses to obscure the real total cost. Below is the complete, categorized breakdown of all charges detected in your agreement.
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

    if "charges" not in st.session_state or st.session_state.charges is None:
        st.markdown(
            """
            <div class="premium-card glow-border-amber" style="background: rgba(245, 158, 11, 0.02); padding: 24px; margin-bottom: 25px;">
                <div style="font-weight: 700; color: #f59e0b; font-size: 16px; margin-bottom: 8px;">⚠️ No Document Analyzed Yet</div>
                <div style="color: #cbd5e1; font-size: 13px; line-height: 1.5;">
                    Please go to the <b>Upload & Analyze</b> page and process a loan agreement to view detected charges.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        return

    charges = st.session_state.charges
    metrics = st.session_state.metrics
    explanations = st.session_state.explanations
    math_examples = st.session_state.math_examples
    transparency = st.session_state.transparency
    
    currency = "₹"

    if not charges:
        st.markdown(
            """
            <div class="premium-card glow-border-indigo" style="background: rgba(99, 102, 241, 0.02); padding: 20px;">
                <div style="color: #cbd5e1; font-size: 13px;">No additional charges or hidden fees were detected in this agreement. It only contains base loan terms.</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        return

    # Compute summary metrics
    total_detected = len(charges)
    verified_vals = sum(1 for c in charges if c.get("value") is not None)
    unspecified_vals = sum(1 for c in charges if c.get("value") is None)
    
    risk_score = transparency["score"]
    if risk_score >= 80:
        overall_risk = "LOW RISK"
        risk_color = "#10B981"
    elif risk_score >= 60:
        overall_risk = "MEDIUM RISK"
        risk_color = "#F59E0B"
    else:
        overall_risk = "HIGH RISK"
        risk_color = "#EF4444"

    # Render summary metrics cards
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(
            f"""<div style="padding: 15px; text-align: center; background: #0F1E33; border: 1px solid rgba(148,163,184,0.1); border-radius: 12px;">
<div style="font-size: 10px; color: #94A3B8; text-transform: uppercase; font-weight: 700; margin-bottom: 5px;">Charges Detected</div>
<div style="font-size: 22px; font-weight: 800; color: #38BDF8; font-family: 'Outfit', sans-serif;">{total_detected}</div>
</div>""",
            unsafe_allow_html=True
        )
    with m2:
        st.markdown(
            f"""<div style="padding: 15px; text-align: center; background: #0F1E33; border: 1px solid rgba(148,163,184,0.1); border-radius: 12px;">
<div style="font-size: 10px; color: #94A3B8; text-transform: uppercase; font-weight: 700; margin-bottom: 5px;">Values Verified</div>
<div style="font-size: 22px; font-weight: 800; color: #10B981; font-family: 'Outfit', sans-serif;">{verified_vals}</div>
</div>""",
            unsafe_allow_html=True
        )
    with m3:
        st.markdown(
            f"""<div style="padding: 15px; text-align: center; background: #0F1E33; border: 1px solid rgba(148,163,184,0.1); border-radius: 12px;">
<div style="font-size: 10px; color: #94A3B8; text-transform: uppercase; font-weight: 700; margin-bottom: 5px;">Values Unspecified</div>
<div style="font-size: 22px; font-weight: 800; color: #F59E0B; font-family: 'Outfit', sans-serif;">{unspecified_vals}</div>
</div>""",
            unsafe_allow_html=True
        )
    with m4:
        st.markdown(
            f"""<div style="padding: 15px; text-align: center; background: #0F1E33; border: 1px solid rgba(148,163,184,0.1); border-radius: 12px;">
<div style="font-size: 10px; color: #94A3B8; text-transform: uppercase; font-weight: 700; margin-bottom: 5px;">Potential Risk Level</div>
<div style="font-size: 16px; font-weight: 800; color: {risk_color}; margin-top: 5px; font-family: 'Space Grotesk', sans-serif;">{overall_risk}</div>
</div>""",
            unsafe_allow_html=True
        )

    st.write("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

    # Categorize charges for display
    upfront = [c for c in charges if c["classification"] in ["ADDITIONAL_COST", "TAX"]]
    optional = [c for c in charges if c["classification"] == "OPTIONAL_COST"]
    conditional = [c for c in charges if c["classification"] in ["CONDITIONAL_COST", "PENALTY"]]
    other = [c for c in charges if c["classification"] not in ["ADDITIONAL_COST", "TAX", "OPTIONAL_COST", "CONDITIONAL_COST", "PENALTY"]]

    # Financial Flow Diagram (Sankey)
    st.markdown(
        """
        <h3 style="margin-top: 25px; margin-bottom: 15px; font-size: 18px; font-family: 'Space Grotesk', sans-serif; font-weight: 700;">📊 Loan Cash Flow Allocation</h3>
        <p style="margin: -10px 0 20px 0; color: #94a3b8; font-size: 12px;">
            A structural visualization showing how your Loan Principal is split between disbursement, upfront deductions, taxes, and interest costs.
        </p>
        """,
        unsafe_allow_html=True
    )

    # Safely extract metrics values with defaults
    metrics_data = metrics or {}
    net_disbursed = float(metrics_data.get('net_disbursed_amount', 0.0) or 0.0)
    upfront_fees = float(metrics_data.get('upfront_fees', 0.0) or 0.0)
    taxes_on_fees = float(metrics_data.get('taxes_on_fees', 0.0) or 0.0)
    loan_amount = float(metrics_data.get('loan_amount', 0.0) or 0.0)
    total_interest = float(metrics_data.get('total_interest', 0.0) or 0.0)
    total_repayment = float(metrics_data.get('total_scheduled_repayment', 0.0) or 0.0)
    mandatory_recurring = float(metrics_data.get('mandatory_recurring_fees', 0.0) or 0.0)

    # Build and show Sankey Diagram
    labels = [
        f"Disbursed Cash<br>{currency}{net_disbursed:,.0f}", # 0
        f"Upfront Fees<br>{currency}{upfront_fees:,.0f}", # 1
        f"Taxes on Fees<br>{currency}{taxes_on_fees:,.0f}", # 2
        f"Loan Principal<br>{currency}{loan_amount:,.0f}", # 3
        f"Interest Cost<br>{currency}{total_interest:,.0f}", # 4
        f"Total Repayment<br>{currency}{total_repayment:,.0f}" # 5
    ]
    sources = [0, 1, 2, 3, 4]
    targets = [3, 3, 3, 5, 5]
    values = [
        net_disbursed,
        upfront_fees,
        taxes_on_fees,
        loan_amount,
        total_interest
    ]

    # Add mandatory recurring fees if any
    if mandatory_recurring > 0:
        labels.append(f"Recurring Fees<br>{currency}{mandatory_recurring:,.0f}") # 6
        sources.append(6)
        targets.append(5)
        values.append(mandatory_recurring)

    fig_sankey = go.Figure(data=[go.Sankey(
        node = dict(
          pad = 20,
          thickness = 15,
          line = dict(color = "rgba(255,255,255,0.06)", width = 0.5),
          label = labels,
          color = ["#10b981", "#fb7185", "#f59e0b", "#6366f1", "#ec4899", "#8b5cf6", "#a855f7"]
        ),
        link = dict(
          source = sources,
          target = targets,
          value = values,
          color = [
              "rgba(16, 185, 129, 0.12)",
              "rgba(251, 113, 133, 0.12)",
              "rgba(245, 158, 11, 0.12)",
              "rgba(99, 102, 241, 0.12)",
              "rgba(236, 72, 153, 0.12)"
          ] + (["rgba(168, 85, 247, 0.12)"] if metrics.get('mandatory_recurring_fees', 0) > 0 else [])
      ))])

    fig_sankey.update_layout(
        font_size=10,
        font_family="Plus Jakarta Sans",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color='#cbd5e1',
        height=280,
        margin=dict(l=10, r=10, t=10, b=10)
    )
    
    st.plotly_chart(fig_sankey, use_container_width=True, config={'displayModeBar': False})

    # Compile upfront chart data
    chart_data = []
    for c in upfront:
        val = c.get("value")
        from modules.financial_engine.fees import calculate_fee_value
        absolute_value = 0.0
        if val is not None and isinstance(val, (int, float)):
            absolute_value = calculate_fee_value(metrics["loan_amount"], val, c.get("unit"))
        
        if absolute_value > 0:
            chart_data.append({
                "Charge": c.get("original_name") or c.get("canonical_name").replace("_", " ").title(),
                "Amount": absolute_value
            })
            
    if chart_data:
        st.markdown(
            """
            <h4 style="margin-top: 25px; margin-bottom: 15px; font-size: 15px; font-family: 'Space Grotesk', sans-serif; font-weight: 700; color: #ffffff;">📊 Upfront Deducted Charges Breakdown</h4>
            """,
            unsafe_allow_html=True
        )
        df = pd.DataFrame(chart_data)
        fig_bar = px.bar(
            df,
            x="Charge",
            y="Amount",
            text="Amount",
            color="Charge",
            labels={"Amount": f"Amount ({currency})"},
            color_discrete_sequence=["#6366f1", "#06b6d4", "#8b5cf6", "#10b981", "#f59e0b"]
        )
        fig_bar.update_traces(texttemplate='₹%{text:,.0f}', textposition='outside', marker_line_color='rgba(0,0,0,0)', opacity=0.85)
        fig_bar.update_layout(
            showlegend=False,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='#cbd5e1',
            font_family="Plus Jakarta Sans",
            height=260,
            margin=dict(l=10, r=10, t=20, b=10),
            xaxis=dict(showgrid=False, linecolor='rgba(255,255,255,0.08)'),
            yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.04)', linecolor='rgba(255,255,255,0.08)')
        )
        st.plotly_chart(fig_bar, use_container_width=True, config={'displayModeBar': False})

    st.markdown("---")

    # Render categorized tabs/views
    tab1, tab2, tab3 = st.tabs(["Upfront & Scheduled Costs", "Conditional & Penalty Charges", "Optional & Other Charges"])
    
    def render_charge_cards(charge_list):
        if not charge_list:
            st.markdown(
                """
                <div style="color: #94a3b8; font-size: 12px; font-style: italic; padding: 15px 0;">No charges found in this category.</div>
                """,
                unsafe_allow_html=True
            )
            return
            
        for c in charge_list:
            name = c.get("original_name") or c.get("canonical_name").replace("_", " ").title()
            canonical_name = c["canonical_name"]
            classification = c["classification"]
            val = c.get("value")
            unit = c.get("unit")
            basis = c.get("basis")
            page = c.get("page", 1)
            source = c.get("source", "ai_extraction")
            confidence = c.get("confidence", "medium")
            evidence = c.get("evidence") or "No direct snippet found."
            
            # Format value string
            if val is None:
                val_str = "Value Not Specified"
                val_color = "#f59e0b"
                status_txt = "KEYWORD DETECTED"
                
                # Unspecified costs are Amber
                glow_class = "glow-border-amber"
                severity = "Medium"
                sev_color = "#F59E0B"
            else:
                if isinstance(val, (int, float)):
                    if unit == "percent":
                        val_str = f"{val}%"
                    else:
                        val_str = f"{currency}{val:,.2f}"
                else:
                    # It's a string (e.g. descriptive text or uncleaned string)
                    val_str = str(val).strip()
                    try:
                        clean_val = val_str.replace(',', '').replace('Rs.', '').replace('INR', '').replace('%', '').strip()
                        float_val = float(clean_val)
                        if unit == "percent":
                            val_str = f"{float_val}%"
                        else:
                            val_str = f"{currency}{float_val:,.2f}"
                    except ValueError:
                        # Fallback for descriptive text clauses
                        if unit == "percent" and "%" not in val_str:
                            val_str = f"{val_str}%"
                        elif unit == "currency" and currency not in val_str and "Rs" not in val_str and "INR" not in val_str:
                            val_str = f"{currency}{val_str}"
                val_color = "#10b981"
                status_txt = "VERIFIED"
                
                # Check for high-risk conditions vs verified standard values
                # Penalties are high risk (Red)
                if classification == "PENALTY" or canonical_name in ["late_payment_fee", "bounce_charge", "default_penalty"]:
                    glow_class = "glow-border-rose"
                    severity = "High"
                    sev_color = "#EF4444"
                else:
                    # Verified standard value
                    glow_class = "glow-border-emerald"
                    severity = "Low"
                    sev_color = "#10B981"

            # Style the card
            st.markdown(
                f"""
                <div class="premium-card {glow_class}" style="padding: 16px 20px; margin-bottom: 12px; background: rgba(255,255,255,0.015);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: 700; font-size: 14px; color: #ffffff;">{name}</span>
                        <span style="font-weight: 800; font-size: 14px; color: {val_color};">{val_str}</span>
                    </div>
                    <div style="display: flex; gap: 8px; margin-top: 8px; flex-wrap: wrap; align-items: center;">
                        <span style="background-color: rgba(255,255,255,0.04); color: #cbd5e1; font-size: 9px; padding: 2px 8px; border-radius: 4px;">Page {page}</span>
                        <span style="background-color: rgba(56, 189, 248, 0.08); color: #38bdf8; font-size: 9px; padding: 2px 8px; border-radius: 4px; text-transform: uppercase;">{confidence} CONFIDENCE</span>
                        <span style="background-color: {sev_color}1a; color: {sev_color}; font-size: 9px; padding: 2px 8px; border-radius: 4px; font-weight: bold; text-transform: uppercase;">{severity} Severity</span>
                        <span style="background-color: {val_color}1a; color: {val_color}; font-size: 9px; padding: 2px 8px; border-radius: 4px; font-weight: bold; text-transform: uppercase; margin-left: 4px;">{status_txt}</span>
                        <span style="background-color: rgba(255,255,255,0.02); color: #94a3b8; font-size: 9px; padding: 2px 8px; border-radius: 4px; margin-left: auto;">{basis or 'flat'}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
            
            # Render explanation and details in expander
            expl = explanations.get(canonical_name)
            m_ex = math_examples.get(canonical_name)
            
            with st.expander(f"🔍 View Details & Evidence for {name}"):
                if expl:
                    st.markdown(f"""
                        <div style="font-size: 13px; color: #cbd5e1; line-height: 1.5; margin-bottom: 10px;">
                            💡 <b>Explanation:</b> {expl}
                        </div>
                    """, unsafe_allow_html=True)
                if m_ex:
                    res_val = m_ex['result']
                    res_str = f"{currency}{res_val:,.2f}" if isinstance(res_val, (int, float)) else str(res_val)
                    st.markdown(f"""
                        <div style="background: rgba(15, 23, 42, 0.4); padding: 12px; border-radius: 8px; font-size: 12px; margin-bottom: 10px; border: 1px dashed rgba(255, 255, 255, 0.08); color: #cbd5e1;">
                            <div style="margin-bottom: 4px; color: #818cf8; font-weight: 700;">🧮 Concrete Calculation Example:</div>
                            <div style="margin-bottom: 4px;"><b>Scenario:</b> {m_ex['scenario']}</div>
                            <div><b>Math:</b> <code style="background: rgba(255,255,255,0.03); padding: 2px 6px; border-radius: 4px; color: #22d3ee; font-family: monospace;">{m_ex['formula']}</code> = <b style="color: #10b981;">{res_str}</b></div>
                        </div>
                    """, unsafe_allow_html=True)
                
                st.markdown(f"""
                    <div style="background-color: rgba(0, 0, 0, 0.25); padding: 12px; border-radius: 8px; font-size: 12px; color: #cbd5e1; border: 1px solid rgba(148, 163, 184, 0.08); font-family: monospace; line-height: 1.5; font-style: italic;">
                        "{evidence}"
                    </div>
                    <div style="font-size: 10px; color: #94a3b8; margin-top: 6px; text-align: right;">
                        Audit Status: <b style="color: {val_color};">{status_txt}</b> &nbsp;|&nbsp; Extraction Method: <b>{source.replace('_', ' ').title()}</b>
                    </div>
                """, unsafe_allow_html=True)
                
            st.markdown("<div style='height: 5px;'></div>", unsafe_allow_html=True)
            
    with tab1:
        st.markdown(
            """
            <h4 style="margin-top: 15px; margin-bottom: 10px; font-size: 15px; font-family: 'Space Grotesk', sans-serif; font-weight: 700; color: #ffffff;">📆 Upfront & Scheduled Costs</h4>
            <p style="color: #94a3b8; font-size: 12px; margin-bottom: 20px;">These charges are guaranteed to occur and are either deducted upfront from your disbursement or added to your scheduled payments.</p>
            """,
            unsafe_allow_html=True
        )
        render_charge_cards(upfront)
        
    with tab2:
        st.markdown(
            """
            <h4 style="margin-top: 15px; margin-bottom: 10px; font-size: 15px; font-family: 'Space Grotesk', sans-serif; font-weight: 700; color: #ffffff;">⚠️ Conditional & Penalty Charges</h4>
            <p style="color: #94a3b8; font-size: 12px; margin-bottom: 20px;">These fees only occur under specific circumstances, such as if you repay the loan early or miss a scheduled payment date.</p>
            """,
            unsafe_allow_html=True
        )
        render_charge_cards(conditional)
        
    with tab3:
        st.markdown(
            """
            <h4 style="margin-top: 15px; margin-bottom: 10px; font-size: 15px; font-family: 'Space Grotesk', sans-serif; font-weight: 700; color: #ffffff;">💡 Optional & Other Charges</h4>
            <p style="color: #94a3b8; font-size: 12px; margin-bottom: 20px;">These charges represent voluntary products (like credit shield insurance) or general administrative line items.</p>
            """,
            unsafe_allow_html=True
        )
        render_charge_cards(optional + other)

