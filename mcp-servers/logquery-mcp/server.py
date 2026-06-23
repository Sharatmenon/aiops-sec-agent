from mcp.server.fastmcp import FastMCP
import duckdb, json, os
from datetime import datetime, timezone

mcp = FastMCP("logquery-mcp", description="Log query MCP server — DuckDB queries across all platform log sources")

BASE = os.path.dirname(os.path.abspath(__file__))
LOGS = os.environ.get("LOGS_PATH", os.path.join(BASE, "../../logs"))

def get_db():
    db = duckdb.connect()
    sources = {
        "logs_istio":    f"{LOGS}/istio.json",
        "logs_keycloak": f"{LOGS}/keycloak.json",
        "logs_argocd":   f"{LOGS}/argocd.json",
        "logs_k8s":      f"{LOGS}/k8s_events.json",
        "logs_openbao":  f"{LOGS}/openbao.json",
        "logs_kafka":    f"{LOGS}/kafka.json",
        "logs_minio":    f"{LOGS}/minio.json",
        "logs_cnpg":     f"{LOGS}/cnpg.json",
        "logs_spark":    f"{LOGS}/spark.json",
    }
    for table, path in sources.items():
        if os.path.exists(path):
            db.execute(f"CREATE TABLE IF NOT EXISTS {table} AS SELECT * FROM read_json_auto('{path}')")
    return db

SCHEMA = """
Tables and key columns:
- logs_istio:    timestamp, src_pod, dst_pod, src_namespace, response_code, tls_status, latency_ms, path
- logs_keycloak: timestamp, event_type, user, realm, client, result, error, ip_address
- logs_argocd:   timestamp, app, event_type, status, health, sync_result, message, revision
- logs_k8s:      timestamp, pod, namespace, reason, type, message, restart_count, phase, node
- logs_openbao:  timestamp, operation, path, result, error, accessor, lease_duration_sec
- logs_kafka:    timestamp, topic, event_type, level, consumer_group, consumer_lag, broker_id, error
- logs_minio:    timestamp, bucket, object, operation, response_code, bytes_transferred, error
- logs_cnpg:     timestamp, cluster, instance, role, event_type, level, connections_active, replication_lag_ms, error
- logs_spark:    timestamp, job_id, job_name, stage_name, event_type, level, failed_tasks, error
Use EPOCH() for time arithmetic. All timestamps are UTC ISO8601.
"""

@mcp.tool()
def query_logs(sql: str) -> str:
    """Run SQL against platform log tables in DuckDB. Use EPOCH() for time window joins."""
    try:
        db = get_db()
        result = db.execute(sql).df()
        return json.dumps({"rows": result.to_dict(orient="records"), "row_count": len(result), "columns": list(result.columns)}, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.tool()
def get_schema() -> str:
    """Return the full schema of all available log tables."""
    return SCHEMA

@mcp.tool()
def get_errors(since_minutes: int = 30) -> str:
    """Get all ERROR/WARN entries across all sources."""
    try:
        db = get_db()
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
                rows = db.execute(q).df().to_dict(orient="records")
                all_errors.extend(rows)
            except:
                pass
        all_errors.sort(key=lambda x: x.get("ts", ""))
        return json.dumps({"errors": all_errors, "total": len(all_errors)}, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.tool()
def get_pod_log_errors(pod_name: str) -> str:
    """Get all K8s warning events for a specific pod."""
    try:
        db = get_db()
        rows = db.execute(f"""
            SELECT CAST(timestamp AS VARCHAR) AS timestamp, reason, message, restart_count
            FROM logs_k8s WHERE pod ILIKE '%{pod_name}%' AND type = 'Warning'
            ORDER BY timestamp
        """).df().to_dict(orient="records")
        return json.dumps({"pod": pod_name, "events": rows, "count": len(rows)}, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})

if __name__ == "__main__":
    mcp.run(transport="sse")
