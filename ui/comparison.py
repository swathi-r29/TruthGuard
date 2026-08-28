import streamlit as st
import pandas as pd
import plotly.express as px
from modules.debt_strategy.ranking import rank_debts, get_strategy_explanation

def render_comparison_page():
    st.markdown(
        """
        <div style="margin-bottom: 25px;">
            <h1 style="margin: 0; background: linear-gradient(135deg, #ffffff 0%, #a5b4fc 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 32px; font-weight: 800; font-family: 'Space Grotesk', sans-serif;">⚖️ Multi-Debt Strategy & Prioritizer</h1>
            <p style="margin: 5px 0 0 0; color: #94a3b8; font-size: 14px; line-height: 1.6;">
                Aggregate and compare all your debts in one workspace. Use mathematical priority models like the Debt Avalanche (highest interest first) or Debt Snowball (lowest balance first) to eliminate debt efficiently.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Initialize comparison list in session state
    if "debts_list" not in st.session_state:
        st.session_state.debts_list = []

    # Auto-import analyzed loan if available and not failed extraction
    if "metrics" in st.session_state and st.session_state.metrics is not None:
        metrics = st.session_state.metrics
        is_failed_extraction = (metrics.get("loan_amount", 0) <= 0.0 and metrics.get("interest_rate_annual", 0) <= 0.0)
        if not is_failed_extraction:
            analyzed_name = f"Analyzed: {st.session_state.doc_name}"
            
            # Check outstanding principal in extracted separately
            extracted = st.session_state.extracted
            outstanding = getattr(extracted, "outstanding_principal", None)
            if outstanding and outstanding.value is not None:
                analyzed_balance = float(outstanding.value)
            else:
                analyzed_balance = float(metrics["loan_amount"])
                
            analyzed_rate = float(metrics["interest_rate_annual"])
            analyzed_emi = float(metrics["emi"])
            
            # Check if already added
            if not any(d["name"] == analyzed_name for d in st.session_state.debts_list):
                st.session_state.debts_list.append({
                    "name": analyzed_name,
                    "balance": float(analyzed_balance),
                    "interest_rate": float(analyzed_rate),
                    "emi": float(analyzed_emi)
                })

    currency = "₹"
    
    # Section 1: Manage Debts
    st.markdown(
        """
        <h3 style="margin-top: 25px; margin-bottom: 15px; font-size: 18px; font-family: 'Space Grotesk', sans-serif; font-weight: 700;">📝 Active Debt Inventory</h3>
        """,
        unsafe_allow_html=True
    )

    # Initialize show_add_form in session state
    if "show_add_form" not in st.session_state:
        st.session_state.show_add_form = False

    # Render add debt form helper
    def render_add_debt_form(inline=False):
        title = "Add a New Debt Manually" if not inline else "➕ Enter Debt Parameters"
        with st.form("add_debt_form", clear_on_submit=True):
            st.markdown(f"<div style='font-size: 13px; font-weight: 700; color: #ffffff; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.03em;'>{title}</div>", unsafe_allow_html=True)
            debt_name = st.text_input("Debt / Loan Name", placeholder="e.g. Credit Card A, Car Loan, BNPL")
            col_b, col_r, col_e = st.columns(3)
            with col_b:
                debt_balance = st.number_input("Outstanding Balance (Principal)", min_value=0.0, step=1000.0, format="%.2f")
            with col_r:
                debt_rate = st.number_input("Annual Interest Rate (%)", min_value=0.0, max_value=100.0, step=0.1, format="%.2f")
            with col_e:
                debt_emi = st.number_input("Monthly Minimum Payment (EMI)", min_value=0.0, step=100.0, format="%.2f")
                
            submitted = st.form_submit_button("Add to prioritizer")
            if submitted and debt_name:
                st.session_state.debts_list.append({
                    "name": debt_name,
                    "balance": debt_balance,
                    "interest_rate": debt_rate,
                    "emi": debt_emi
                })
                st.session_state.show_add_form = False
                st.success(f"Added '{debt_name}' successfully!")
                st.rerun()

    # Form to add a new debt if there are already debts
    if st.session_state.debts_list:
        with st.expander("➕ Add a New Debt Manually"):
            render_add_debt_form(inline=False)
    else:
        # Display empty state
        st.markdown(
            """
            <div style="text-align: center; padding: 40px 20px; border-radius: 16px; border: 1px dashed rgba(148,163,184,0.15); background: #0F1E33; margin-bottom: 25px;">
                <div style="font-size: 40px; margin-bottom: 15px;">⚖️</div>
                <h3 style="margin: 0; color: #F8FAFC; font-size: 18px; font-weight: 700; font-family: 'Space Grotesk', sans-serif;">No debts in your portfolio yet.</h3>
                <p style="margin: 10px auto 25px auto; color: #94A3B8; font-size: 13px; max-width: 500px; line-height: 1.5;">
                    Add multiple debts to compare repayment strategies and discover the most efficient payoff order.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # Display 3 strategy preview cards side-by-side
        st.markdown(
            """
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-bottom: 25px;">
                <div class="premium-card glow-border-cyan" style="background: #0F1E33; border: 1px solid rgba(148,163,184,0.08); padding: 20px; margin-bottom: 0;">
                    <div style="font-weight: 700; color: #38BDF8; font-size: 14px; margin-bottom: 8px; font-family: 'Space Grotesk', sans-serif;">AVALANCHE</div>
                    <p style="font-size: 11px; color: #cbd5e1; line-height: 1.5; margin: 0;">
                        Pay highest-interest debt first. Best for minimizing interest.
                    </p>
                </div>
                <div class="premium-card glow-border-indigo" style="background: #0F1E33; border: 1px solid rgba(148,163,184,0.08); padding: 20px; margin-bottom: 0;">
                    <div style="font-weight: 700; color: #6366F1; font-size: 14px; margin-bottom: 8px; font-family: 'Space Grotesk', sans-serif;">SNOWBALL</div>
                    <p style="font-size: 11px; color: #cbd5e1; line-height: 1.5; margin: 0;">
                        Pay smallest balance first. Best for quick wins and motivation.
                    </p>
                </div>
                <div class="premium-card glow-border-emerald" style="background: #0F1E33; border: 1px solid rgba(148,163,184,0.08); padding: 20px; margin-bottom: 0;">
                    <div style="font-weight: 700; color: #10B981; font-size: 14px; margin-bottom: 8px; font-family: 'Space Grotesk', sans-serif;">AI RECOMMENDED</div>
                    <p style="font-size: 11px; color: #cbd5e1; line-height: 1.5; margin: 0;">
                        Recommend a strategy based on user priorities and debt characteristics.
                    </p>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        if not st.session_state.show_add_form:
            if st.button("➕ Add Your First Debt"):
                st.session_state.show_add_form = True
                st.rerun()
        else:
            render_add_debt_form(inline=True)
            if st.button("Cancel"):
                st.session_state.show_add_form = False
                st.rerun()
                
        return

    # List of debts with custom card format and delete action
    st.markdown(
        """
        <div style="font-size: 13px; color: #94a3b8; margin-bottom: 15px;">Currently entered debt profiles:</div>
        """,
        unsafe_allow_html=True
    )
    
    # Render active list
    for idx, d in enumerate(st.session_state.debts_list):
        col_card, col_btn = st.columns([8, 1])
        with col_card:
            st.markdown(
                f"""
                <div class="premium-card glow-border-indigo" style="padding: 14px 20px; margin-bottom: 12px; background: rgba(255,255,255,0.015);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: 700; font-size: 14px; color: #ffffff;">{d['name']}</span>
                        <span style="font-size: 11px; color: #94a3b8;">
                            Balance: <b style="color: #cbd5e1;">{currency}{d['balance']:,.2f}</b> &nbsp;|&nbsp;
                            Rate: <b style="color: #cbd5e1;">{d['interest_rate']}% p.a.</b> &nbsp;|&nbsp;
                            EMI: <b style="color: #cbd5e1;">{currency}{d['emi']:,.2f}</b>
                        </span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with col_btn:
            # Inline spacing for button alignment
            st.write("<div style='height: 4px;'></div>", unsafe_allow_html=True)
            if st.button("🗑️", key=f"del_debt_{idx}", help=f"Remove {d['name']}"):
                st.session_state.debts_list.pop(idx)
                st.rerun()
    
    # Clear all button
    col_clear, _ = st.columns([2, 8])
    with col_clear:
        if st.button("🗑️ Clear All Debts"):
            st.session_state.debts_list = []
            st.rerun()

    # Compute portfolio summary metrics
    total_debt = sum(d["balance"] for d in st.session_state.debts_list)
    total_monthly = sum(d["emi"] for d in st.session_state.debts_list)
    weighted_interest = (sum(d["balance"] * d["interest_rate"] for d in st.session_state.debts_list) / total_debt) if total_debt > 0 else 0
    
    st.markdown("---")
    st.markdown(
        """
        <h3 style="margin-top: 25px; margin-bottom: 15px; font-size: 18px; font-family: 'Space Grotesk', sans-serif; font-weight: 700;">📊 Portfolio Aggregates</h3>
        """,
        unsafe_allow_html=True
    )
    
    col_ag_d, col_ag_m, col_ag_r = st.columns(3)
    with col_ag_d:
        st.markdown(
            f"""
            <div class="premium-card glow-border-indigo" style="padding: 16px; text-align: center; background: #0F1E33; border: 1px solid rgba(148,163,184,0.1); margin-bottom: 0;">
                <div style="font-size: 10px; color: #94A3B8; text-transform: uppercase; font-weight: 700; margin-bottom: 5px;">Total Debt Balance</div>
                <div style="font-size: 20px; font-weight: 800; color: #ffffff; font-family: 'Outfit', sans-serif;">{currency}{total_debt:,.2f}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col_ag_m:
        st.markdown(
            f"""
            <div class="premium-card glow-border-emerald" style="padding: 16px; text-align: center; background: #0F1E33; border: 1px solid rgba(148,163,184,0.1); margin-bottom: 0;">
                <div style="font-size: 10px; color: #94A3B8; text-transform: uppercase; font-weight: 700; margin-bottom: 5px;">Total Monthly Payment</div>
                <div style="font-size: 20px; font-weight: 800; color: #ffffff; font-family: 'Outfit', sans-serif;">{currency}{total_monthly:,.2f}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col_ag_r:
        st.markdown(
            f"""
            <div class="premium-card glow-border-cyan" style="padding: 16px; text-align: center; background: #0F1E33; border: 1px solid rgba(148,163,184,0.1); margin-bottom: 0;">
                <div style="font-size: 10px; color: #94A3B8; text-transform: uppercase; font-weight: 700; margin-bottom: 5px;">Weighted Avg Interest</div>
                <div style="font-size: 20px; font-weight: 800; color: #38BDF8; font-family: 'Outfit', sans-serif;">{weighted_interest:.2f}% p.a.</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("---")

    # Section 2: Strategy Selector & Explanations
    st.markdown(
        """
        <h3 style="margin-top: 25px; margin-bottom: 15px; font-size: 18px; font-family: 'Space Grotesk', sans-serif; font-weight: 700;">⚙️ Prioritization Engine</h3>
        """,
        unsafe_allow_html=True
    )
    strategy = st.radio(
        "Select optimization strategy:",
        [
            "Avalanche (Highest Interest First) — Math Optimized", 
            "Snowball (Smallest Balance First) — Psychological Win",
            "AI Recommended (Balanced Hybrid) — Customized Priority"
        ]
    )
    
    strategy_key = "avalanche" if "Avalanche" in strategy else ("snowball" if "Snowball" in strategy else "ai_recommended")
    explanation = get_strategy_explanation(strategy_key)
    
    # Display strategy explanation box
    st.markdown(
        f"""
        <div class="premium-card glow-border-indigo" style="background: rgba(99, 102, 241, 0.01); padding: 20px; margin-bottom: 25px;">
            <h5 style="margin: 0 0 10px 0; color: #ffffff; font-size: 14px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.02em;">📘 Strategy Model: {explanation['title']}</h5>
            <p style="font-size: 13px; margin: 6px 0; color: #cbd5e1; line-height: 1.5;"><b>Mechanism:</b> {explanation['mechanism']}</p>
            <p style="font-size: 13px; margin: 6px 0; color: #10b981;"><b>✓ Advantages:</b> {explanation['pros']}</p>
            <p style="font-size: 13px; margin: 6px 0; color: #f43f5e;"><b>✗ Drawbacks:</b> {explanation['cons']}</p>
            <p style="font-size: 13px; margin: 10px 0 0 0; color: #06b6d4; font-style: italic;">💡 <b>Professional Recommendation:</b> {explanation['advice']}</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Section 3: Ranking results
    ranked = rank_debts(st.session_state.debts_list, strategy_key)
    
    st.markdown(
        """
        <h3 style="margin-top: 25px; margin-bottom: 15px; font-size: 18px; font-family: 'Space Grotesk', sans-serif; font-weight: 700;">🏆 Your Optimized Payoff Roadmap</h3>
        <p style="margin: -10px 0 20px 0; color: #94a3b8; font-size: 12px; line-height: 1.5;">
            Allocate all excess monthly cash towards <b>Priority #1</b>. Maintain minimum monthly payments on all other debts. Once Priority #1 is fully extinguished, roll its entire monthly budget into Priority #2.
        </p>
        """,
        unsafe_allow_html=True
    )

    for r in ranked:
        rank = r["priority_rank"]
        name = r["name"]
        bal = r["balance"]
        rate = r["interest_rate"]
        emi = r["emi"]
        
        # Color borders and labels based on rank priority
        if rank == 1:
            glow_class = "glow-border-emerald"
            bg_color = "rgba(16, 185, 129, 0.02)"
            badge_html = """
            <div style="text-align: right; display: flex; flex-direction: column; align-items: flex-end;">
                <span style="background-color: #10b981; color: white; padding: 4px 12px; border-radius: 12px; font-size: 11px; font-weight: 800; letter-spacing: 0.05em; animation: pulse_emerald 1.8s infinite; text-transform: uppercase;">Attack First</span>
            </div>
            """
        else:
            glow_class = "glow-border-indigo"
            bg_color = "rgba(255, 255, 255, 0.01)"
            badge_html = """
            <div style="text-align: right;">
                <span style="background-color: rgba(255,255,255,0.04); color: #cbd5e1; border: 1px solid rgba(255,255,255,0.06); padding: 4px 12px; border-radius: 12px; font-size: 11px; font-weight: 700; letter-spacing: 0.03em; text-transform: uppercase;">Pay Minimum</span>
            </div>
            """
        
        st.markdown(
            f"""
            <style>
            @keyframes pulse_emerald {{
                0% {{ box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4); }}
                70% {{ box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }}
                100% {{ box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }}
            }}
            </style>
            <div class="premium-card {glow_class}" style="background-color: {bg_color}; padding: 16px 20px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <span style="font-size: 16px; font-weight: 800; color: #ffffff; font-family: 'Space Grotesk', sans-serif;">#{rank} &nbsp; {name}</span>
                    <div style="font-size: 12px; color: #94a3b8; margin-top: 5px;">
                        Balance: <b style="color: #cbd5e1;">{currency}{bal:,.2f}</b> &nbsp;|&nbsp; Rate: <b style="color: #cbd5e1;">{rate}% p.a.</b> &nbsp;|&nbsp; Minimum EMI: <b style="color: #cbd5e1;">{currency}{emi:,.2f}</b>
                    </div>
                </div>
                {badge_html}
            </div>
            """,
            unsafe_allow_html=True
        )

    # Plotly bar chart visualizing ranking balances or interest rates
    st.markdown(
        """
        <h3 style="margin-top: 30px; margin-bottom: 15px; font-size: 18px; font-family: 'Space Grotesk', sans-serif; font-weight: 700;">📊 Debt Composition Comparison</h3>
        """,
        unsafe_allow_html=True
    )
    df_ranked = pd.DataFrame(ranked)
    
    fig = px.bar(
        df_ranked,
        x="name",
        y="balance",
        color="interest_rate",
        labels={"name": "Debt Name", "balance": f"Outstanding Balance ({currency})", "interest_rate": "Interest Rate (%)"},
        color_continuous_scale="Tealrose"
    )
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color='#cbd5e1',
        font_family="Plus Jakarta Sans",
        height=280,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(showgrid=False, linecolor='rgba(255,255,255,0.08)'),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.04)', linecolor='rgba(255,255,255,0.08)')
    )
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
