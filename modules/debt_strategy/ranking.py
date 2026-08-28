from typing import List, Dict, Any

def rank_debts(debts: List[Dict[str, Any]], strategy: str = "avalanche") -> List[Dict[str, Any]]:
    """
    Ranks a list of debts based on the selected strategy.
    
    Each debt dictionary must have:
      - 'name': str
      - 'balance': float
      - 'interest_rate': float
      - 'emi': float
      
    Strategies:
      - 'avalanche': Highest interest rate first (mathematically optimal, saves most interest).
      - 'snowball': Smallest balance first (psychological wins, frees up EMI cash flow quickly).
      - 'ai_recommended': Hybrid optimization ranking interest and balance.
    """
    if not debts:
        return []
        
    strat_clean = strategy.strip().lower()
    
    # Copy debts to avoid in-place modification
    ranked_debts = [dict(d) for d in debts]
    
    if strat_clean == "snowball":
        # Sort by balance ascending (smallest balance first)
        ranked_debts.sort(key=lambda x: x.get("balance", 0.0))
    elif strat_clean == "ai_recommended":
        # Hybrid Strategy: weight interest rate and balance to optimize cost and cash flow
        # Score = interest_rate - (balance / 100000.0) -> high interest gets preference, but lower balances get tie-breakers
        ranked_debts.sort(key=lambda x: x.get("interest_rate", 0.0) - (x.get("balance", 0.0) / 100000.0), reverse=True)
    else:
        # Default to avalanche: sort by interest rate descending (highest interest rate first)
        ranked_debts.sort(key=lambda x: x.get("interest_rate", 0.0), reverse=True)
        
    # Append priority ranking indices
    for idx, d in enumerate(ranked_debts):
        d["priority_rank"] = idx + 1
        
    return ranked_debts

def get_strategy_explanation(strategy: str) -> Dict[str, str]:
    """
    Returns consumer-friendly educational explanations of the strategy properties.
    """
    strat_clean = strategy.strip().lower()
    if strat_clean == "snowball":
        return {
            "title": "Debt Snowball (Smallest Balance First)",
            "mechanism": "Focus all extra payments on the smallest balance first, while paying minimums on others.",
            "pros": "Creates quick psychological wins as you watch accounts close entirely. Frees up minimum monthly payments to apply to larger debts.",
            "cons": "You will pay more total interest over time compared to the Avalanche strategy, especially if your largest debts have high interest rates.",
            "advice": "Consider this strategy if you feel overwhelmed and need early motivators to stay on track."
        }
    elif strat_clean == "ai_recommended":
        return {
            "title": "AI Recommended (Customized Balanced Hybrid)",
            "mechanism": "Prioritizes high-interest loans while dynamically weighting smaller balances to accelerate cash flow recovery.",
            "pros": "Captures the interest-saving power of the Avalanche method, but triggers faster closures when interest rates are closely matched.",
            "cons": "A minor deviation from absolute mathematical optimization if high-balance loans are bypassed temporarily.",
            "advice": "Best overall choice for balancing mental momentum with actual interest cost reduction."
        }
        
    return {
        "title": "Debt Avalanche (Highest Interest First)",
        "mechanism": "Focus all extra payments on the debt with the highest interest rate, while paying minimums on others.",
        "pros": "Mathematically optimal. You pay the absolute minimum amount of total interest and get out of debt faster overall.",
        "cons": "It might take longer to see the first account close if your highest-interest debt is also your largest balance.",
        "advice": "Highly recommended for minimizing the actual cost of borrowing. It is the most financially efficient path."
    }
