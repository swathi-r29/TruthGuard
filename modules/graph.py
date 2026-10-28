import logging
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END
from modules.schemas import GraphState
from modules.agents import (
    retriever_node,
    evidence_prep_node,
    synthesizer_node,
    critic_node,
    resolution_node
)

logger = logging.getLogger("truthguard.graph")

def increment_revision_node(state: GraphState) -> Dict[str, Any]:
    count = state.get("revision_count", 0) + 1
    logger.info(f"Advancing revision count to {count} based on critic feedback.")
    return {"revision_count": count}

def should_revise_edge(state: GraphState) -> Literal["increment_revision", "resolution"]:
    critique = state.get("critique")
    count = state.get("revision_count", 0)
    if critique and (not critique.is_valid) and count < 2:
        return "increment_revision"
    return "resolution"

def build_truthguard_graph():
    """
    Constructs the LangGraph StateGraph:
    retriever -> evidence_prep -> synthesizer -> critic -> [conditional] -> resolution -> END
                                                       ^         |
                                                       |__ inc __|
    """
    workflow = StateGraph(GraphState)

    # Add Nodes
    workflow.add_node("retriever", retriever_node)
    workflow.add_node("evidence_prep", evidence_prep_node)
    workflow.add_node("synthesizer", synthesizer_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("increment_revision", increment_revision_node)
    workflow.add_node("resolution", resolution_node)

    # Set Entry Point
    workflow.set_entry_point("retriever")

    # Add Edges
    workflow.add_edge("retriever", "evidence_prep")
    workflow.add_edge("evidence_prep", "synthesizer")
    workflow.add_edge("synthesizer", "critic")

    # Conditional routing from critic
    workflow.add_conditional_edges(
        "critic",
        should_revise_edge,
        {
            "increment_revision": "increment_revision",
            "resolution": "resolution"
        }
    )
    workflow.add_edge("increment_revision", "synthesizer")
    workflow.add_edge("resolution", END)

    app = workflow.compile()
    return app

# Compiled graph singleton
truthguard_graph = build_truthguard_graph()

