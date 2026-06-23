import duckdb, os

BASE = os.path.dirname(os.path.abspath(__file__))

def get_db():
    db = duckdb.connect()
    sources = {
        "logs_istio":    os.path.join(BASE, "logs/istio.json"),
        "logs_keycloak": os.path.join(BASE, "logs/keycloak.json"),
        "logs_argocd":   os.path.join(BASE, "logs/argocd.json"),
        "logs_k8s":      os.path.join(BASE, "logs/k8s_events.json"),
        "logs_openbao":  os.path.join(BASE, "logs/openbao.json"),
        "logs_kafka":    os.path.join(BASE, "logs/kafka.json"),
        "logs_minio":    os.path.join(BASE, "logs/minio.json"),
        "logs_cnpg":     os.path.join(BASE, "logs/cnpg.json"),
        "logs_spark":    os.path.join(BASE, "logs/spark.json"),
    }
    for table, path in sources.items():
        if os.path.exists(path):
            db.execute(f"CREATE TABLE IF NOT EXISTS {table} AS SELECT * FROM read_json_auto('{path}')")
    return db

SCHEMA = """
Available tables and key columns:
- logs_istio:    timestamp, src_pod, dst_pod, src_namespace, dst_namespace, response_code, tls_status, latency_ms, path, method
- logs_keycloak: timestamp, event_type, user, realm, client, result, error, ip_address, session_id
- logs_argocd:   timestamp, app, event_type, status, health, sync_result, message, revision
- logs_k8s:      timestamp, pod, namespace, reason, type, message, restart_count, phase, node
- logs_openbao:  timestamp, operation, path, result, error, accessor, lease_duration_sec, ip_address
- logs_kafka:    timestamp, topic, event_type, level, consumer_group, consumer_lag, broker_id, error
- logs_minio:    timestamp, bucket, object, operation, response_code, bytes_transferred, error, caller_pod
- logs_cnpg:     timestamp, cluster, instance, role, event_type, level, connections_active, connections_max, replication_lag_ms, error
- logs_spark:    timestamp, job_id, job_name, stage_name, event_type, level, failed_tasks, error, executor_id
All timestamps are UTC ISO8601. Use EPOCH() for time arithmetic.
"""
