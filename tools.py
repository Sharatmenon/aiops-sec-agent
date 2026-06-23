"""
tools.py — Stub tools for local PoC (no Docker required).
For MCP-backed tools, use tools_mcp.py with docker compose up.
"""

from langchain_core.tools import tool
from db import get_db, SCHEMA
import json

_db = get_db()

# ── Log query tools ───────────────────────────────────────────────────────────

@tool
def query_logs(sql: str) -> str:
    """Run SQL against platform log tables in DuckDB.
    Tables: logs_istio, logs_keycloak, logs_argocd, logs_k8s, logs_openbao,
            logs_kafka, logs_minio, logs_cnpg, logs_spark.
    Use EPOCH() for time arithmetic. Call get_log_schema() if unsure of columns."""
    try:
        result = _db.execute(sql).df()
        return json.dumps({
            "rows": result.to_dict(orient="records"),
            "row_count": len(result),
            "columns": list(result.columns),
        }, default=str)
    except Exception as e:
        return json.dumps({"error": str(e), "hint": "Check column names via get_log_schema()"})

@tool
def get_log_schema() -> str:
    """Return the schema of all available platform log tables."""
    return SCHEMA

@tool
def get_errors(since_minutes: int = 30) -> str:
    """Get all ERROR/WARN entries across every log source."""
    queries = {
        "k8s":      "SELECT 'k8s' AS source, CAST(timestamp AS VARCHAR) AS ts, reason AS event, message AS detail FROM logs_k8s WHERE type='Warning'",
        "keycloak": "SELECT 'keycloak' AS source, CAST(timestamp AS VARCHAR) AS ts, event_type AS event, error AS detail FROM logs_keycloak WHERE result='FAILURE' AND error IS NOT NULL",
        "openbao":  "SELECT 'openbao' AS source, CAST(timestamp AS VARCHAR) AS ts, operation AS event, error AS detail FROM logs_openbao WHERE result='FAILURE' AND error IS NOT NULL",
        "kafka":    "SELECT 'kafka' AS source, CAST(timestamp AS VARCHAR) AS ts, event_type AS event, error AS detail FROM logs_kafka WHERE level IN ('ERROR','WARN') AND error IS NOT NULL",
        "minio":    "SELECT 'minio' AS source, CAST(timestamp AS VARCHAR) AS ts, operation AS event, error AS detail FROM logs_minio WHERE response_code >= 400 AND error IS NOT NULL",
        "cnpg":     "SELECT 'cnpg' AS source, CAST(timestamp AS VARCHAR) AS ts, event_type AS event, error AS detail FROM logs_cnpg WHERE level IN ('ERROR','WARN') AND error IS NOT NULL",
        "spark":    "SELECT 'spark' AS source, CAST(timestamp AS VARCHAR) AS ts, event_type AS event, error AS detail FROM logs_spark WHERE level='ERROR' AND error IS NOT NULL",
    }
    all_errors = []
    for _, q in queries.items():
        try:
            rows = _db.execute(q).df().to_dict(orient="records")
            all_errors.extend(rows)
        except:
            pass
    all_errors.sort(key=lambda x: x.get("ts", ""))
    return json.dumps({"errors": all_errors, "total": len(all_errors)}, default=str)

@tool
def get_pod_log_errors(pod_name: str) -> str:
    """Get all K8s warning events for a specific pod."""
    try:
        rows = _db.execute(f"""
            SELECT CAST(timestamp AS VARCHAR) AS timestamp, reason, message, restart_count
            FROM logs_k8s
            WHERE pod ILIKE '%{pod_name}%' AND type = 'Warning'
            ORDER BY timestamp
        """).df().to_dict(orient="records")
        return json.dumps({"pod": pod_name, "events": rows, "count": len(rows)}, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})

# ── Kubectl stub tools ────────────────────────────────────────────────────────

PODS = [
    {"name": "aiops-sec-agent-8e2b", "namespace": "secops", "status": "Running",          "node": "aks-nodepool-002", "restarts": 0, "ready": "1/1"},
    {"name": "aiops-sec-agent-7d9f", "namespace": "secops", "status": "CrashLoopBackOff", "node": "aks-nodepool-001", "restarts": 5, "ready": "0/1"},
    {"name": "keycloak-0",           "namespace": "secops", "status": "Running",          "node": "aks-nodepool-001", "restarts": 0, "ready": "1/1"},
    {"name": "kafka-broker-0",       "namespace": "secops", "status": "Running",          "node": "aks-nodepool-002", "restarts": 1, "ready": "1/1"},
    {"name": "kafka-broker-1",       "namespace": "secops", "status": "Pending",          "node": None,               "restarts": 0, "ready": "0/1"},
    {"name": "openbao-0",            "namespace": "secops", "status": "Running",          "node": "aks-nodepool-001", "restarts": 0, "ready": "1/1"},
    {"name": "minio-0",              "namespace": "secops", "status": "Running",          "node": "aks-nodepool-002", "restarts": 0, "ready": "1/1"},
    {"name": "cnpg-rw-0",            "namespace": "secops", "status": "Running",          "node": "aks-nodepool-001", "restarts": 0, "ready": "1/1"},
    {"name": "nozomi-proxy-2c1a",    "namespace": "secops", "status": "Running",          "node": "aks-nodepool-001", "restarts": 0, "ready": "1/1"},
]

@tool
def get_pods(namespace: str = "secops") -> str:
    """List all pods in a namespace with status and restart count."""
    pods = [p for p in PODS if p["namespace"] == namespace]
    return json.dumps({"namespace": namespace, "pods": pods})

@tool
def describe_pod(pod_name: str, namespace: str = "secops") -> str:
    """Get detailed info and recent events for a specific pod."""
    pod = next((p for p in PODS if p["name"] == pod_name), None)
    if not pod:
        return json.dumps({"error": f"Pod {pod_name} not found"})
    events = []
    if pod["status"] == "CrashLoopBackOff":
        events = [{"reason": "BackOff", "message": "exit code 1 — secret fetch failed: openbao returned 403", "count": pod["restarts"]}]
    return json.dumps({"pod": pod, "events": events})

@tool
def get_pod_logs(pod_name: str, namespace: str = "secops", tail_lines: int = 20) -> str:
    """Fetch recent stdout logs from a pod container."""
    log_map = {
        "aiops-sec-agent-7d9f": [
            "2026-06-03T10:00:01Z ERROR Failed to read secret secops/azure-openai-key: 403 Forbidden — token expired",
            "2026-06-03T10:00:01Z FATAL Cannot start without Azure OpenAI credentials. Exiting.",
        ],
        "aiops-sec-agent-8e2b": [
            "2026-06-03T10:03:11Z INFO  Successfully fetched secret secops/azure-openai-key",
            "2026-06-03T10:03:20Z INFO  Listening on :8080 — ready",
        ],
    }
    return json.dumps({"pod": pod_name, "logs": log_map.get(pod_name, ["No logs available"])})

@tool
def get_nodes() -> str:
    """Get AKS node pool status and resource utilisation."""
    return json.dumps({"nodes": [
        {"name": "aks-nodepool-001", "status": "Ready",    "cpu_used_pct": 72, "memory_used_pct": 68, "pod_count": 12},
        {"name": "aks-nodepool-002", "status": "Ready",    "cpu_used_pct": 45, "memory_used_pct": 51, "pod_count": 8},
        {"name": "aks-nodepool-003", "status": "NotReady", "cpu_used_pct": 0,  "memory_used_pct": 0,  "pod_count": 0},
    ]})

@tool
def rollout_restart(deployment: str, namespace: str = "secops") -> str:
    """Trigger a rollout restart for a deployment. Requires human approval before calling."""
    return json.dumps({"action": "rollout_restart", "deployment": deployment,
                       "status": "triggered", "note": "STUB — no actual restart in PoC"})

# ── ArgoCD stub tools ─────────────────────────────────────────────────────────

APPS = {
    "aiops-sec-agent": {"health": "Degraded",  "status": "OutOfSync", "revision": "a1b2c3d", "last_sync": "2026-06-03T09:55:30Z"},
    "keycloak":        {"health": "Healthy",   "status": "Synced",    "revision": "b2c3d4e", "last_sync": "2026-06-03T10:01:45Z"},
    "openbao":         {"health": "Healthy",   "status": "Synced",    "revision": "c3d4e5f", "last_sync": "2026-06-03T10:02:45Z"},
    "kafka":           {"health": "Degraded",  "status": "Synced",    "revision": "d4e5f6g", "last_sync": "2026-06-03T09:00:00Z"},
    "minio":           {"health": "Healthy",   "status": "Synced",    "revision": "e5f6g7h", "last_sync": "2026-06-03T08:00:00Z"},
}

@tool
def list_apps(project: str = "secops") -> str:
    """List all ArgoCD applications with sync and health status."""
    return json.dumps({"apps": [{"name": k, **v} for k, v in APPS.items()]})

@tool
def get_app(app_name: str) -> str:
    """Get detailed status for a specific ArgoCD application."""
    app = APPS.get(app_name)
    return json.dumps({"app": app_name, **app} if app else {"error": f"App {app_name} not found"})

@tool
def get_degraded_apps() -> str:
    """Return all ArgoCD apps that are not Healthy."""
    degraded = [{"name": k, **v} for k, v in APPS.items() if v["health"] != "Healthy"]
    return json.dumps({"degraded_apps": degraded, "count": len(degraded)})

@tool
def get_app_history(app_name: str) -> str:
    """Get recent deployment history for an ArgoCD app."""
    history = {
        "aiops-sec-agent": [
            {"revision": "a1b2c3d", "deployed_at": "2026-06-03T09:55:30Z", "status": "Succeeded"},
            {"revision": "9z8y7x6", "deployed_at": "2026-06-02T14:00:00Z", "status": "Succeeded"},
        ]
    }
    return json.dumps({"app": app_name, "history": history.get(app_name, [])})

@tool
def rollback_app(app_name: str, revision: str) -> str:
    """Roll back an ArgoCD app to a previous revision. Requires human approval."""
    return json.dumps({"action": "rollback", "app": app_name, "to_revision": revision,
                       "argocd_cmd": f"argocd app rollback {app_name} --revision {revision}",
                       "note": "STUB — no actual rollback in PoC"})

# ── Tool lists per agent ──────────────────────────────────────────────────────

LOG_TOOLS         = [query_logs, get_log_schema, get_errors, get_pod_log_errors]
TRIAGE_TOOLS      = [query_logs, get_errors]
REMEDIATION_TOOLS = [get_pods, describe_pod, get_pod_logs, get_nodes,
                     list_apps, get_app, get_degraded_apps, get_app_history,
                     rollout_restart, rollback_app]
