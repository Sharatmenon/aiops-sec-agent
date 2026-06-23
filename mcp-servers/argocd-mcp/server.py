from mcp.server.fastmcp import FastMCP
import json
from datetime import datetime, timezone

mcp = FastMCP("argocd-mcp", description="ArgoCD MCP server — GitOps application operations")

APPS = {
    "aiops-sec-agent": {
        "name": "aiops-sec-agent", "project": "secops", "namespace": "secops",
        "status": "OutOfSync", "health": "Degraded",
        "revision": "a1b2c3d", "repo": "git@github.com:your-org/secops-gitops.git",
        "path": "apps/aiops-sec-agent", "dest_server": "https://aks-secops.eastus.azmk8s.io",
        "last_sync": "2026-06-03T09:55:30Z", "sync_policy": "automated",
        "images": ["jfrog.secops.internal/aiops-sec-agent:1.0.3"],
    },
    "keycloak": {
        "name": "keycloak", "project": "secops", "namespace": "secops",
        "status": "Synced", "health": "Healthy",
        "revision": "b2c3d4e", "repo": "git@github.com:your-org/secops-gitops.git",
        "path": "apps/keycloak", "dest_server": "https://aks-secops.eastus.azmk8s.io",
        "last_sync": "2026-06-03T10:01:45Z", "sync_policy": "automated",
        "images": ["quay.io/keycloak/keycloak:24.0.4"],
    },
    "openbao": {
        "name": "openbao", "project": "secops", "namespace": "secops",
        "status": "Synced", "health": "Healthy",
        "revision": "c3d4e5f", "repo": "git@github.com:your-org/secops-gitops.git",
        "path": "apps/openbao", "dest_server": "https://aks-secops.eastus.azmk8s.io",
        "last_sync": "2026-06-03T10:02:45Z", "sync_policy": "manual",
        "images": ["openbao/openbao:2.0.0"],
    },
    "kafka": {
        "name": "kafka", "project": "secops", "namespace": "secops",
        "status": "Synced", "health": "Degraded",
        "revision": "d4e5f6g", "repo": "git@github.com:your-org/secops-gitops.git",
        "path": "apps/kafka", "dest_server": "https://aks-secops.eastus.azmk8s.io",
        "last_sync": "2026-06-03T09:00:00Z", "sync_policy": "automated",
        "images": ["strimzi/kafka:0.39.0-kafka-3.6.1"],
    },
    "minio": {
        "name": "minio", "project": "secops", "namespace": "secops",
        "status": "Synced", "health": "Healthy",
        "revision": "e5f6g7h", "repo": "git@github.com:your-org/secops-gitops.git",
        "path": "apps/minio", "dest_server": "https://aks-secops.eastus.azmk8s.io",
        "last_sync": "2026-06-03T08:00:00Z", "sync_policy": "automated",
        "images": ["quay.io/minio/minio:RELEASE.2024-01-01"],
    },
}

@mcp.tool()
def list_apps(project: str = "secops") -> str:
    """List all ArgoCD applications with sync and health status."""
    apps = [{"name": a["name"], "status": a["status"], "health": a["health"],
             "revision": a["revision"], "last_sync": a["last_sync"]}
            for a in APPS.values() if a["project"] == project]
    return json.dumps({"project": project, "apps": apps, "timestamp": datetime.now(timezone.utc).isoformat()})

@mcp.tool()
def get_app(app_name: str) -> str:
    """Get detailed status for a specific ArgoCD application."""
    app = APPS.get(app_name)
    if not app:
        return json.dumps({"error": f"App '{app_name}' not found"})
    return json.dumps({"app": app, "timestamp": datetime.now(timezone.utc).isoformat()})

@mcp.tool()
def get_degraded_apps() -> str:
    """Return all apps that are not Healthy."""
    degraded = [{"name": a["name"], "health": a["health"], "status": a["status"], "last_sync": a["last_sync"]}
                for a in APPS.values() if a["health"] != "Healthy"]
    return json.dumps({"degraded_apps": degraded, "count": len(degraded), "timestamp": datetime.now(timezone.utc).isoformat()})

@mcp.tool()
def get_app_history(app_name: str) -> str:
    """Get recent deployment history for an app."""
    history = {
        "aiops-sec-agent": [
            {"revision": "a1b2c3d", "deployed_at": "2026-06-03T09:55:30Z", "triggered_by": "automated", "status": "Succeeded"},
            {"revision": "9z8y7x6", "deployed_at": "2026-06-02T14:00:00Z", "triggered_by": "automated", "status": "Succeeded"},
        ]
    }
    return json.dumps({"app": app_name, "history": history.get(app_name, []), "timestamp": datetime.now(timezone.utc).isoformat()})

@mcp.tool()
def rollback_app(app_name: str, revision: str) -> str:
    """Roll back an application to a specific git revision."""
    if app_name not in APPS:
        return json.dumps({"error": f"App '{app_name}' not found"})
    return json.dumps({
        "action": "rollback", "app": app_name, "to_revision": revision,
        "argocd_cmd": f"argocd app rollback {app_name} --revision {revision}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "note": "STUB — no actual rollback performed in local PoC"
    })

if __name__ == "__main__":
    mcp.run(transport="sse")
