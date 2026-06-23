from mcp.server.fastmcp import FastMCP
import json
from datetime import datetime, timezone

mcp = FastMCP("kubectl-mcp", description="kubectl MCP server — AKS pod and node operations")

PODS = [
    {"name": "aiops-sec-agent-8e2b", "namespace": "secops", "status": "Running",          "node": "aks-nodepool-002", "restarts": 0,  "age": "2m",  "ready": "1/1", "ip": "10.244.1.15"},
    {"name": "aiops-sec-agent-7d9f", "namespace": "secops", "status": "CrashLoopBackOff", "node": "aks-nodepool-001", "restarts": 5,  "age": "10m", "ready": "0/1", "ip": "10.244.0.22"},
    {"name": "keycloak-0",           "namespace": "secops", "status": "Running",          "node": "aks-nodepool-001", "restarts": 0,  "age": "1d",  "ready": "1/1", "ip": "10.244.0.10"},
    {"name": "kafka-broker-0",       "namespace": "secops", "status": "Running",          "node": "aks-nodepool-002", "restarts": 1,  "age": "1d",  "ready": "1/1", "ip": "10.244.1.8"},
    {"name": "kafka-broker-1",       "namespace": "secops", "status": "Pending",          "node": None,               "restarts": 0,  "age": "5m",  "ready": "0/1", "ip": None},
    {"name": "openbao-0",            "namespace": "secops", "status": "Running",          "node": "aks-nodepool-001", "restarts": 0,  "age": "1d",  "ready": "1/1", "ip": "10.244.0.12"},
    {"name": "minio-0",              "namespace": "secops", "status": "Running",          "node": "aks-nodepool-002", "restarts": 0,  "age": "1d",  "ready": "1/1", "ip": "10.244.1.5"},
    {"name": "cnpg-rw-0",            "namespace": "secops", "status": "Running",          "node": "aks-nodepool-001", "restarts": 0,  "age": "1d",  "ready": "1/1", "ip": "10.244.0.9"},
    {"name": "nozomi-proxy-2c1a",    "namespace": "secops", "status": "Running",          "node": "aks-nodepool-001", "restarts": 0,  "age": "1d",  "ready": "1/1", "ip": "10.244.0.18"},
]

@mcp.tool()
def get_pods(namespace: str = "secops") -> str:
    """Get all pods in a namespace with status, restarts, node assignment."""
    pods = [p for p in PODS if p["namespace"] == namespace]
    return json.dumps({"namespace": namespace, "pods": pods, "timestamp": datetime.now(timezone.utc).isoformat()})

@mcp.tool()
def describe_pod(pod_name: str, namespace: str = "secops") -> str:
    """Get detailed info for a specific pod including recent events."""
    pod = next((p for p in PODS if p["name"] == pod_name and p["namespace"] == namespace), None)
    if not pod:
        return json.dumps({"error": f"Pod {pod_name} not found in namespace {namespace}"})
    events = []
    if pod["status"] == "CrashLoopBackOff":
        events = [{"reason": "BackOff", "message": "exit code 1 — secret fetch failed: openbao returned 403", "count": pod["restarts"]}]
    elif pod["status"] == "Pending":
        events = [{"reason": "Unschedulable", "message": "0/3 nodes available: insufficient memory", "count": 1}]
    return json.dumps({"pod": pod, "events": events, "timestamp": datetime.now(timezone.utc).isoformat()})

@mcp.tool()
def get_pod_logs(pod_name: str, namespace: str = "secops", tail_lines: int = 20) -> str:
    """Fetch recent stdout logs from a pod container."""
    logs = {
        "aiops-sec-agent-7d9f": [
            "2026-06-03T10:00:00Z INFO  Starting aiops-sec-agent v1.0.3",
            "2026-06-03T10:00:01Z INFO  Fetching secrets from OpenBao at https://openbao.secops.svc:8200",
            "2026-06-03T10:00:01Z ERROR Failed to read secret secops/azure-openai-key: 403 Forbidden — token expired",
            "2026-06-03T10:00:01Z FATAL Cannot start without Azure OpenAI credentials. Exiting.",
        ],
        "aiops-sec-agent-8e2b": [
            "2026-06-03T10:03:10Z INFO  Starting aiops-sec-agent v1.0.3",
            "2026-06-03T10:03:11Z INFO  Successfully fetched secret secops/azure-openai-key from OpenBao",
            "2026-06-03T10:03:12Z INFO  Connected to Keycloak realm: secops",
            "2026-06-03T10:03:20Z INFO  Listening on :8080 — ready",
        ],
    }
    pod_logs = logs.get(pod_name, [f"No logs available for {pod_name}"])
    return json.dumps({"pod": pod_name, "logs": pod_logs[-tail_lines:], "timestamp": datetime.now(timezone.utc).isoformat()})

@mcp.tool()
def rollout_restart(deployment: str, namespace: str = "secops") -> str:
    """Trigger a rollout restart for a deployment."""
    return json.dumps({
        "action": "rollout_restart", "deployment": deployment, "namespace": namespace,
        "status": "triggered", "message": f"deployment.apps/{deployment} restarted",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "note": "STUB — no actual restart performed in local PoC"
    })

@mcp.tool()
def get_nodes() -> str:
    """Get AKS node pool status and resource utilisation."""
    return json.dumps({"nodes": [
        {"name": "aks-nodepool-001", "status": "Ready",    "cpu_used_pct": 72, "memory_used_pct": 68, "pod_count": 12},
        {"name": "aks-nodepool-002", "status": "Ready",    "cpu_used_pct": 45, "memory_used_pct": 51, "pod_count": 8},
        {"name": "aks-nodepool-003", "status": "NotReady", "cpu_used_pct": 0,  "memory_used_pct": 0,  "pod_count": 0},
    ], "timestamp": datetime.now(timezone.utc).isoformat()})

if __name__ == "__main__":
    mcp.run(transport="sse")
