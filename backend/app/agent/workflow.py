"""Claim graph topology. Node names and routes are checkpoint-compatible."""

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.runtime import Runtime

from app.agent.nodes import ClaimNodes
from app.agent.state import ClaimGraphState, ReviewExecution


def build_claim_workflow(
    nodes: ClaimNodes, checkpointer: BaseCheckpointSaver, resources=None,
) -> CompiledStateGraph:
    builder = StateGraph(ClaimGraphState, context_schema=ReviewExecution)
    for name, step in (
        ("extract", nodes.extract),
        ("validate", nodes.validate),
        ("evaluate_policy", nodes.evaluate_policy),
        ("detect_duplicates", nodes.detect_duplicates),
        ("score_anomaly", nodes.score_anomaly),
        ("decide", nodes.decide),
        ("wait_clarification", nodes.wait_clarification),
        ("wait_review", nodes.wait_review),
        ("apply_review", nodes.apply_review),
    ):
        if resources is not None and name not in ("wait_clarification", "wait_review", "apply_review"):
            builder.add_node(name, _durable_step(resources, name, step))
        elif resources is not None and name == "apply_review":
            def durable_review(state, runtime: Runtime[ReviewExecution]):
                with resources.transaction():
                    return nodes.apply_review(state, runtime)
            builder.add_node(name, durable_review)
        else:
            builder.add_node(name, step)
    builder.add_conditional_edges(START, lambda s: s["stage"],
                                  ["extract", "wait_clarification", "wait_review"])
    builder.add_conditional_edges("extract", lambda s: s["stage"],
                                  ["validate", "wait_clarification"])
    for source, target in (
        ("validate", "evaluate_policy"),
        ("evaluate_policy", "detect_duplicates"),
        ("detect_duplicates", "score_anomaly"),
        ("score_anomaly", "decide"),
    ):
        builder.add_edge(source, target)
    builder.add_conditional_edges("decide", lambda s: s["stage"],
                                  [END, "wait_clarification", "wait_review"])
    builder.add_edge("wait_clarification", "extract")
    builder.add_edge("wait_review", "apply_review")
    builder.add_edge("apply_review", END)
    return builder.compile(checkpointer=checkpointer)


def _durable_step(resources, name, step):
    def invoke(state: ClaimGraphState):
        return resources.run_step(name, state, lambda: step(state))
    return invoke
