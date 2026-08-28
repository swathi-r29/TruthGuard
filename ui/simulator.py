import streamlit as st
import pandas as pd
import plotly.express as px
from modules.debt_strategy.payoff_simulator import simulate_loan_payoff
import plotly.graph_objects as go

def render_simulator_page():
    st.markdown(
        """
        <div style="margin-bottom: 25px;">
            <h1 style="margin: 0; background: linear-gradient(135deg, #ffffff 0%, #a5b4fc 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 32px; font-weight: 800; font-family: 'Space Grotesk', sans-serif;">🧮 Payoff Acceleration Simulator</h1>
            <p style="margin: 5px 0 0 0; color: #94a3b8; font-size: 14px; line-height: 1.6;">
                Calculate interest savings and schedule compression by prepaying additional principal. Extra payments bypass amortized interest structures.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Check if active document exists and was extracted successfully
    active_document_exists = False
    is_failed_extraction = False
    
    if "metrics" in st.session_state and st.session_state.metrics is not None:
        metrics = st.session_state.metrics
        is_failed_extraction = (metrics.get("loan_amount", 0) <= 0.0 and metrics.get("interest_rate_annual", 0) <= 0.0)
        if not is_failed_extraction:
            active_document_exists = True

    if active_document_exists:
        metrics = st.session_state.metrics
        extracted = st.session_state.extracted
        
        # Look up outstanding_principal separately
        outstanding = getattr(extracted, "outstanding_principal", None)
        if outstanding and outstanding.value is not None:
            default_bal = float(outstanding.value)
            has_outstanding = True
        else:
            default_bal = float(metrics["loan_amount"])
            has_outstanding = False
            
        default_rate = float(metrics["interest_rate_annual"])
        default_emi = float(metrics["emi"])
        doc_name = st.session_state.doc_name
        
        st.markdown(
            f"""
            <div class="premium-card glow-border-indigo" style="padding: 12px 18px; background: rgba(99, 102, 241, 0.02); font-size: 12px; color: #cbd5e1; margin-bottom: 20px;">
                ⚙️ Prepopulated with active document terms: <b>{doc_name}</b>
            </div>
            """,
            unsafe_allow_html=True
        )
        if not has_outstanding:
            st.markdown(
                """
                <div class="premium-card glow-border-amber" style="padding: 10px 15px; background: rgba(245, 158, 11, 0.02); font-size: 11px; color: #f59e0b; margin-bottom: 20px;">
                    ⚠️ Current outstanding balance was not found. Simulation uses the original principal as an estimate.
                </div>
                """,
                unsafe_allow_html=True
            )
    else:
        default_bal = 100000.0
        default_rate = 12.0
        default_emi = 5000.0
        st.markdown(
            """
            <div style="background-color: rgba(245, 158, 11, 0.1); border: 1px solid #F59E0B; padding: 8px 16px; border-radius: 8px; font-weight: 700; color: #F59E0B; font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; display: inline-block; margin-bottom: 20px;">
                ⚠️ DEMO DATA — NOT FROM YOUR DOCUMENT
            </div>
            <div class="premium-card glow-border-amber" style="padding: 12px 18px; background: rgba(245, 158, 11, 0.02); font-size: 12px; color: #cbd5e1; margin-bottom: 20px;">
                Demo Mode — No analyzed document. Using standard mock defaults. You can adjust the parameters below manually.
            </div>
            """,
            unsafe_allow_html=True
        )

    currency = "₹"

    # Input Parameters
    st.markdown(
        """
        <h4 style="margin-top: 15px; margin-bottom: 15px; font-size: 15px; font-family: 'Space Grotesk', sans-serif; font-weight: 700; color: #ffffff;">⚙️ Simulation Settings</h4>
        """,
        unsafe_allow_html=True
    )
    col1, col2, col3 = st.columns(3)
    with col1:
        balance = st.number_input("Outstanding Loan Balance", min_value=1.0, value=max(1.0, default_bal), step=5000.0, format="%.2f")
    with col2:
        rate = st.number_input("Stated Annual Interest Rate (%)", min_value=0.1, max_value=100.0, value=max(0.1, default_rate), step=0.5, format="%.2f")
    with col3:
        emi = st.number_input("Current Monthly EMI Payment", min_value=1.0, value=max(1.0, default_emi), step=200.0, format="%.2f")

    st.markdown("---")

    # Extra Payments
    st.markdown(
        """
        <h4 style="margin-top: 15px; margin-bottom: 15px; font-size: 15px; font-family: 'Space Grotesk', sans-serif; font-weight: 700; color: #ffffff;">🚀 Prepayment Strategy</h4>
        """,
        unsafe_allow_html=True
    )
    col_ext_m, col_ext_o, col_ext_t = st.columns(3)
    with col_ext_m:
        extra_monthly = st.slider("Extra Monthly Principal Payment", min_value=0.0, max_value=emi * 3, value=1000.0, step=100.0, format="₹%d")
    with col_ext_o:
        one_time_payment = st.number_input("One-time Lump Sum Payment", min_value=0.0, value=0.0, step=1000.0, format="%.2f")
    with col_ext_t:
        one_time_month = st.number_input("Payment Month for Lump Sum", min_value=1, max_value=360, value=1, step=1)

    # Save to session state for the report
    st.session_state.simulation_extra_monthly = extra_monthly

    # Run simulation
    sim_result = simulate_loan_payoff(
        balance=balance,
        rate_annual=rate,
        current_emi=emi,
        extra_monthly=extra_monthly,
        one_time_payment=one_time_payment,
        one_time_month=one_time_month
    )

    if not sim_result.get("success"):
        st.error(sim_result.get("error", "Failed to run simulation."))
        return

    # Store simulation in session state for reports
    st.session_state.simulation = sim_result

    # Savings Metrics Dashboard
    st.markdown(
        """
        <h4 style="margin-top: 25px; margin-bottom: 15px; font-size: 15px; font-family: 'Space Grotesk', sans-serif; font-weight: 700; color: #ffffff;">💰 Savings Calculation Result</h4>
        """,
        unsafe_allow_html=True
    )
    months_saved = sim_result["months_saved"]
    interest_saved = sim_result["interest_saved"]
    normal_total_interest = sim_result["normal_total_interest"]
    pct_reduction = (interest_saved / normal_total_interest * 100) if normal_total_interest > 0 else 0.0
    
    st.markdown(
        f"""
        <div class="premium-card glow-border-emerald" style="background: rgba(16, 185, 129, 0.02); padding: 24px; margin-bottom: 25px;">
            <div style="font-size: 11px; color: #94A3B8; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 15px;">🚀 Prepayment Impact Assessment</div>
            <div style="display: flex; flex-wrap: wrap; gap: 20px; justify-content: space-between; align-items: center;">
                <div>
                    <span style="font-size: 11px; color: #94A3B8; font-weight: 700; text-transform: uppercase; letter-spacing: 0.03em;">YOU COULD SAVE</span>
                    <h1 style="margin: 5px 0 0 0; color: #10B981; font-size: 34px; font-weight: 800; font-family: 'Outfit', sans-serif;">{currency}{interest_saved:,.0f}</h1>
                    <div style="margin-top: 4px; font-size: 11px; color: #cbd5e1; font-weight: 600;">INTEREST SAVED</div>
                    <span style="background: rgba(16, 185, 129, 0.1); color: #10B981; border: 1px solid rgba(16, 185, 129, 0.2); font-size: 9px; font-weight: 800; padding: 3px 8px; border-radius: 4px; display: inline-block; margin-top: 8px;">{pct_reduction:.1f}% INTEREST REDUCTION</span>
                </div>
                <div style="text-align: right;">
                    <span style="font-size: 11px; color: #94A3B8; font-weight: 700; text-transform: uppercase; letter-spacing: 0.03em;">FASTER PAYOFF</span>
                    <h1 style="margin: 5px 0 0 0; color: #38BDF8; font-size: 34px; font-weight: 800; font-family: 'Outfit', sans-serif;">{months_saved} <span style="font-size: 20px; font-weight: 500; color: #cbd5e1;">Months</span></h1>
                    <div style="margin-top: 4px; font-size: 11px; color: #cbd5e1; font-weight: 600;">FASTER PAYOFF</div>
                    <span style="background: rgba(56, 189, 248, 0.1); color: #38BDF8; border: 1px solid rgba(56, 189, 248, 0.2); font-size: 9px; font-weight: 800; padding: 3px 8px; border-radius: 4px; display: inline-block; margin-top: 8px;">CLOSE IN {sim_result['accelerated_months']} MONTHS</span>
                </div>
            </div>
            <div style="border-top: 1px solid rgba(148,163,184,0.15); margin-top: 20px; padding-top: 15px; display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; text-align: center; font-size: 12px;">
                <div>
                    <div style="color: #94A3B8;">Normal Duration</div>
                    <div style="font-weight: 700; color: #ffffff; margin-top: 2px;">{sim_result['normal_months']} Months</div>
                </div>
                <div>
                    <div style="color: #94A3B8;">Accelerated Duration</div>
                    <div style="font-weight: 700; color: #38BDF8; margin-top: 2px;">{sim_result['accelerated_months']} Months</div>
                </div>
                <div>
                    <div style="color: #94A3B8;">Total Scheduled Repayment</div>
                    <div style="font-weight: 700; color: #cbd5e1; margin-top: 2px;">
                        <span style="text-decoration: line-through; font-size: 10px; color: #ef4444; margin-right: 5px;">{currency}{sim_result['normal_total_repayment']:,.2f}</span>
                        <span style="color: #10b981; font-weight: 800;">{currency}{sim_result['accelerated_total_repayment']:,.2f}</span>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("---")

    # Decay Plot (Balance Over Time)
    st.markdown(
        """
        <h4 style="margin-top: 25px; margin-bottom: 15px; font-size: 15px; font-family: 'Space Grotesk', sans-serif; font-weight: 700; color: #ffffff;">📈 Balance Paydown Timeline</h4>
        """,
        unsafe_allow_html=True
    )
    
    normal_schedule = sim_result["normal_schedule"]
    accelerated_schedule = sim_result["accelerated_schedule"]
    normal_months = sim_result["normal_months"]
    accelerated_months = sim_result["accelerated_months"]
    
    plot_data = []
    plot_data.append({"Month": 0, "Normal Balance (₹)": balance, "Accelerated Balance (₹)": balance})
    
    normal_map = {item["month"]: item["closing_balance"] for item in normal_schedule}
    acc_map = {item["month"]: item["closing_balance"] for item in accelerated_schedule}
    
    max_months = max(normal_months, accelerated_months)
    for m in range(1, max_months + 1):
        plot_data.append({
            "Month": m,
            "Normal Balance (₹)": normal_map.get(m, 0.0) if m <= normal_months else 0.0,
            "Accelerated Balance (₹)": acc_map.get(m, 0.0) if m <= accelerated_months else 0.0
        })
        
    df_plot = pd.DataFrame(plot_data)
    
    # Styled Line chart using Area Fill
    fig_decay = go.Figure()
    fig_decay.add_trace(go.Scatter(
        x=df_plot["Month"],
        y=df_plot["Normal Balance (₹)"],
        mode='lines',
        name='Standard Schedule',
        line=dict(color='#EF4444', width=3),
        fill='tozeroy',
        fillcolor='rgba(239, 68, 68, 0.06)',
        hovertemplate="Month %{x}<br>Standard: ₹%{y:,.2f}<extra></extra>"
    ))
    fig_decay.add_trace(go.Scatter(
        x=df_plot["Month"],
        y=df_plot["Accelerated Balance (₹)"],
        mode='lines',
        name='Accelerated Schedule',
        line=dict(color='#10B981', width=3),
        fill='tozeroy',
        fillcolor='rgba(16, 185, 129, 0.08)',
        hovertemplate="Month %{x}<br>Accelerated: ₹%{y:,.2f}<extra></extra>"
    ))
    
    # Add Standard Closure Marker
    fig_decay.add_trace(go.Scatter(
        x=[normal_months],
        y=[0.0],
        mode='markers+text',
        name='Standard Closure',
        text=[f'M{normal_months}'],
        textposition="top center",
        marker=dict(color='#EF4444', size=11, symbol='circle'),
        hovertemplate="Standard Closure: Month %{x}<extra></extra>"
    ))
    # Add Accelerated Closure Marker
    fig_decay.add_trace(go.Scatter(
        x=[accelerated_months],
        y=[0.0],
        mode='markers+text',
        name='Accelerated Closure',
        text=[f'M{accelerated_months}'],
        textposition="top center",
        marker=dict(color='#10B981', size=13, symbol='star'),
        hovertemplate="Accelerated Closure: Month %{x}<extra></extra>"
    ))
    
    fig_decay.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color='#cbd5e1',
        font_family="Plus Jakarta Sans",
        height=280,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(showgrid=False, linecolor='rgba(255,255,255,0.08)', title_text="Month"),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.04)', linecolor='rgba(255,255,255,0.08)', title_text=f"Balance ({currency})"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig_decay, use_container_width=True, config={'displayModeBar': False})

    st.markdown("---")

    # Comparison Table
    st.markdown(
        """
        <h4 style="margin-top: 25px; margin-bottom: 15px; font-size: 15px; font-family: 'Space Grotesk', sans-serif; font-weight: 700; color: #ffffff;">📊 Scenario Comparison</h4>
        """,
        unsafe_allow_html=True
    )
    comp_df = pd.DataFrame([
        {
            "Metric": "Total Months to Payoff",
            "Normal Schedule": f"{normal_months} months",
            "Accelerated Schedule": f"{accelerated_months} months",
            "Savings / Difference": f"{months_saved} months faster"
        },
        {
            "Metric": "Total Interest Cost",
            "Normal Schedule": f"{currency}{sim_result['normal_total_interest']:,.2f}",
            "Accelerated Schedule": f"{currency}{sim_result['accelerated_total_interest']:,.2f}",
            "Savings / Difference": f"{currency}{interest_saved:,.2f} saved"
        },
        {
            "Metric": "Total Repayment",
            "Normal Schedule": f"{currency}{sim_result['normal_total_repayment']:,.2f}",
            "Accelerated Schedule": f"{currency}{sim_result['accelerated_total_repayment']:,.2f}",
            "Savings / Difference": f"{currency}{interest_saved:,.2f} saved"
        }
    ])
    st.table(comp_df)
