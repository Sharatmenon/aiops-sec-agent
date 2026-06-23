"""
agents.py — AgentState and three LangGraph sub-agents for aiops-sec-agent.
"""

import os
from typing import TypedDict, Annotated
from langgraph.prebuilt import create_react_agent
from langgraph.graph.message import add_messages
from langchain_anthropic import ChatAnthropic

USE_MCP = os.environ.get("USE_MCP_TOOLS", "false").lower() == "true"

if USE_MCP:
    from tools_mcp import LOG_TOOLS, TRIAGE_TOOLS, REMEDIATION_TOOLS
else:
    from tools import LOG_TOOLS, TRIAGE_TOOLS, REMEDIATION_TOOLS

class AgentState(TypedDict):
    messages:     Annotated[list, add_messages]
    log_summary:  str
    alerts:       list
    pod_status:   str
    final_report: str

model = ChatAnthropic(model="claude-sonnet-4-5", temperature=0)

log_correlation_agent = create_react_agent(
    model,
    tools=LOG_TOOLS,
    prompt=(
        "You are a log correlation expert for an OT/ICS security platform running on Azure AKS. "
        "Your job: query log tables across Istio, Keycloak, ArgoCD, K8s, OpenBao, "
        "Kafka, MinIO, CNPG, and Spark to identify error patterns and causal chains. "
        "Always start with get_errors() for a broad view, then drill down with query_logs(). "
        "Use time-window JOINs (EPOCH() arithmetic) to find correlated events across sources. "
        "Return a structured summary: root cause, affected components, timeline, evidence SQL."
    )
)

alert_triage_agent = create_react_agent(
    model,
    tools=TRIAGE_TOOLS,
    prompt=(
        "You are a security alert triage expert specialising in OT/ICS and cloud-native platforms. "
        "Given log findings, your job is to: "
        "1. Score each alert HIGH/MEDIUM/LOW based on impact and blast radius. "
        "2. Deduplicate repeated alerts into single incidents. "
        "3. Tag each alert with the relevant MITRE ATLAS technique where applicable. "
        "4. Distinguish security incidents from operational incidents. "
        "Return a structured alert list with: severity, atlas_tag, affected_pods, "
        "business_impact, and recommended_action."
    )
)

remediation_agent = create_react_agent(
    model,
    tools=REMEDIATION_TOOLS,
    prompt=(
        "You are an SRE for an AKS-based OT/ICS security platform. "
        "Given a set of triaged alerts, your job is to: "
        "1. Check current pod and node health. "
        "2. Check ArgoCD app status for degraded or out-of-sync apps. "
        "3. Correlate infrastructure state with the alerts. "
        "4. Suggest specific remediation actions with exact commands. "
        "IMPORTANT: Never call rollout_restart or rollback_app without explicitly stating "
        "'REQUIRES HUMAN APPROVAL' in your response. "
        "Return: current_state summary, recommended_actions list, approval_required flag."
    )
)
