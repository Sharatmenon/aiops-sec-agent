"""
graph.py — LangGraph StateGraph for aiops-sec-agent.
Supervisor orchestrates: log correlation → alert triage → remediation → final report.
"""

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage
from agents import AgentState, model, log_correlation_agent, alert_triage_agent, remediation_agent


def log_correlation_node(state: AgentState) -> dict:
    print("\n[supervisor] → log_correlation_agent")
    result = log_correlation_agent.invoke({"messages": state["messages"]})
    summary = result["messages"][-1].content
    print(f"[log_correlation_agent] done — {len(summary)} chars")
    return {"log_summary": summary}


def alert_triage_node(state: AgentState) -> dict:
    print("\n[supervisor] → alert_triage_agent")
    result = alert_triage_agent.invoke({"messages": [HumanMessage(content=(
        f"Triage the following log findings into a structured alert list.\n\n"
        f"LOG FINDINGS:\n{state['log_summary']}\n\n"
        f"Score severity, deduplicate, tag with MITRE ATLAS techniques, "
        f"and identify which are security vs operational incidents."
    ))]})
    alerts_text = result["messages"][-1].content
    print(f"[alert_triage_agent] done — {len(alerts_text)} chars")
    return {"alerts": [alerts_text]}


def remediation_node(state: AgentState) -> dict:
    print("\n[supervisor] → remediation_agent")
    alerts_context = state["alerts"][0] if state["alerts"] else "No alerts"
    result = remediation_agent.invoke({"messages": [HumanMessage(content=(
        f"Given these triaged alerts, check the current state of the OT/ICS platform "
        f"and recommend specific remediation actions.\n\n"
        f"TRIAGED ALERTS:\n{alerts_context}\n\n"
        f"Check pods, nodes, and ArgoCD app health. "
        f"Suggest remediation with exact commands where applicable."
    ))]})
    pod_status = result["messages"][-1].content
    print(f"[remediation_agent] done — {len(pod_status)} chars")
    return {"pod_status": pod_status}


def compile_report_node(state: AgentState) -> dict:
    print("\n[supervisor] → compiling final report")
    report = model.invoke([HumanMessage(content=(
        "You are the AIOps security supervisor. Compile a structured security operations report "
        "from the findings below. Format it exactly as:\n\n"
        "# AIOps Security Incident Report\n"
        "## Executive Summary\n"
        "(2-3 sentences: what happened, when, impact)\n\n"
        "## Root Cause\n"
        "(the single originating fault)\n\n"
        "## Timeline\n"
        "(chronological events with timestamps)\n\n"
        "## Alert List\n"
        "(table: severity | component | atlas_tag | description)\n\n"
        "## Current Platform State\n"
        "(pod health, ArgoCD status)\n\n"
        "## Recommended Actions\n"
        "(numbered list, flag any requiring human approval)\n\n"
        "## ATLAS Techniques Observed\n"
        "(technique ID | name | evidence)\n\n"
        "---\n"
        f"LOG CORRELATION FINDINGS:\n{state['log_summary']}\n\n"
        f"TRIAGED ALERTS:\n{state['alerts'][0] if state['alerts'] else 'none'}\n\n"
        f"INFRASTRUCTURE STATE:\n{state['pod_status']}"
    ))])
    print("[supervisor] report compiled")
    return {"final_report": report.content}


def build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("log_correlation", log_correlation_node)
    builder.add_node("alert_triage",    alert_triage_node)
    builder.add_node("remediation",     remediation_node)
    builder.add_node("compile_report",  compile_report_node)
    builder.set_entry_point("log_correlation")
    builder.add_edge("log_correlation", "alert_triage")
    builder.add_edge("alert_triage",    "remediation")
    builder.add_edge("remediation",     "compile_report")
    builder.add_edge("compile_report",  END)
    return builder.compile()


graph = build_graph()
