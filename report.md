# AIOps Security Incident Report

## Executive Summary

On 2026-06-03 between 09:59:45 and 10:04:00 UTC, an OpenBao secret lease expiration triggered a cascading failure across the OT/ICS security platform. The `aiops-sec-agent` pod entered CrashLoopBackOff, causing authentication failures, Kafka consumer disconnections, database connection exhaustion (100/100), MinIO storage quota breach (95%), and Spark job failures. Manual SRE intervention at 10:02:15 UTC restored the OpenBao lease and restarted the affected pod, resolving the incident by 10:04:00 UTC with no data loss.

## Root Cause

OpenBao Vault Secrets Operator (VSO) failed to auto-renew the lease for `secret/data/secops/azure-openai-key` (accessor: `accessor-abc123`) at 09:59:45 UTC, causing the `aiops-sec-agent` pod to lose authentication credentials and enter a crash loop that cascaded across dependent services.

## Timeline

| Time (UTC) | Source | Event |
|------------|--------|-------|
| 09:59:45 | OpenBao | **TRIGGER**: Lease renewal failed - "lease not found or already expired" |
| 09:59:50 | Keycloak | Token refresh failed - "Token expired" |
| 10:00:00 | OpenBao | Read operation denied - "403 permission denied: token expired" |
| 10:00:00 | CNPG | MAX_CONNECTIONS_REACHED (100/100) |
| 10:00:01 | K8s | aiops-sec-agent-7d9f BackOff (restart #1) |
| 10:00:05 | Keycloak | Login failed - "Invalid client credentials" (3x retries) |
| 10:00:05 | Kafka | Consumer disconnected - SessionTimeoutException |
| 10:00:20-01:20 | K8s | aiops-sec-agent-7d9f BackOff (restarts #2-5) |
| 10:00:30 | MinIO | PUT failed - "507 Insufficient Storage" (95% full) |
| 10:00:30 | CNPG | Deadlock detected (process 1234 ↔ txn 5678) |
| 10:00:32 | Spark | Task failed - S3Exception: 507 Insufficient Storage |
| 10:00:35 | Spark | Job aborted - spark-job-001 (secops-log-aggregation) |
| 10:01:30 | K8s | aiops-sec-agent-7d9f enters CrashLoopBackOff |
| 10:02:00 | K8s | kafka-broker-0 Unhealthy (liveness probe failed) |
| 10:02:00 | ArgoCD | OpenBao app degraded - VSO failed to sync secret |
| **10:02:15** | ArgoCD | **REMEDIATION START**: SRE manual sync triggered |
| 10:02:45 | ArgoCD | OpenBao sync succeeded - VSO secret lease renewed |
| 10:03:00 | ArgoCD | Manual rollout restart - aiops-sec-agent |
| **10:04:00** | ArgoCD | **RESOLVED**: aiops-sec-agent-8e2b Healthy |

## Alert List

| Severity | Component | ATLAS Tag | Description |
|----------|-----------|-----------|-------------|
| 🔴 CRITICAL | openbao-0 | AML.T0010 | Secret lease expiration - 4 consecutive renewal failures for accessor-abc123; authentication system compromised |
| 🔴 HIGH | keycloak-0 | AML.T0010.001 | Authentication failures - 3 failed login attempts from svc-aiops-sec-agent (IP: 10.0.1.45); potential credential stuffing |
| 🔴 HIGH | aiops-sec-agent-7d9f | AML.T0034 | CrashLoopBackOff - 5 restarts; AI/ML security monitoring unavailable for 4m 15s; threat detection blind spot |
| 🟠 MEDIUM | cnpg-rw-0 | AML.T0029 | Connection pool exhaustion - 100/100 max connections; database unavailable; ML pipeline degraded |
| 🟠 MEDIUM | minio-0 | AML.T0029 | Storage quota breach - secops-data bucket 95% full; blocking ML artifact writes and log aggregation |
| 🟠 MEDIUM | spark-job-001 | AML.T0040 | Job failure - secops-log-aggregation aborted due to S3 storage exhaustion; security event correlation disrupted |
| 🟡 LOW | kafka-broker-0 | AML.T0029 | Consumer disconnection - SessionTimeoutException; temporary message processing delay; no data loss |
| 🟡 LOW | cnpg-rw-0 | N/A | Transient deadlock - process 1234 ↔ txn 5678; auto-resolved; likely symptom of connection exhaustion |

## Current Platform State

**Pod Health:**
- ✅ `aiops-sec-agent-8e2b`: Running (0 restarts) - Healthy
- ❌ `aiops-sec-agent-7d9f`: Terminated (5 restarts) - **Requires cleanup**
- ⚠️ `kafka-broker-0`: Running (liveness probe recovering)
- ⚠️ `kafka-broker-1`: Pending (unscheduled) - **Node capacity issue**
- ⚠️ `cnpg-rw-0`: Running (connections normalizing)
- ⚠️ `minio-0`: Running (95% storage utilization) - **Action required**

**ArgoCD Application Status:**
- ✅ `openbao`: Healthy + Synced (recovered 10:02:45)
- ✅ `keycloak`: Healthy + Synced (recovered 10:01:45)
- 🔴 `aiops-sec-agent`: Degraded + OutOfSync - **Requires sync to cleanup stale pod**
- ⚠️ `kafka`: Degraded + Synced - **broker-1 unschedulable**

**Infrastructure:**
- 🔴 `aks-nodepool-003`: NotReady (0 pods) - **Node offline**
- ⚠️ `aks-nodepool-001`: High utilization (72% CPU, 68% memory, 12 pods)
- ✅ `aks-nodepool-002`: Healthy (45% CPU, 51% memory, 8 pods)

## Recommended Actions

### Immediate (0-30 minutes)
1. Sync ArgoCD app `aiops-sec-agent` to cleanup stale pod `aiops-sec-agent-7d9f` (no approval required)
2. Investigate node failure `aks-nodepool-003` and determine recovery path (no approval required)
3. Reschedule `kafka-broker-1` by deleting pending pod to trigger rescheduling (no approval required)
4. Audit OpenBao access logs for accessor `accessor-abc123` for unauthorized access (no approval required)
5. Audit Keycloak logs for service account `svc-aiops-sec-agent` authentication attempts (no approval required)

### Short-term (1-4 hours)
6. Execute MinIO storage cleanup: purge logs older than 30 days from `secops-data` bucket (no approval required)
7. Restart failed Spark job `spark-log-aggregation-manual` after storage cleanup (no approval required)
8. Verify CNPG connection pool recovery and kill idle connections if needed (no approval required)
9. **⚠️ Rotate service account credentials for `svc-aiops-sec-agent` (REQUIRES HUMAN APPROVAL)**

### Configuration Changes (4-24 hours)
10. Increase CNPG max_connections from 100 to 200 and deploy PgBouncer via GitOps (no approval required)
11. Implement MinIO lifecycle policy (30-day retention for logs, 90-day for models) (no approval required)
12. Configure OpenBao VSO auto-renewal at 50% TTL threshold (1800s for 1h leases) via GitOps (no approval required)

### Monitoring Enhancements (1-7 days)
13. Deploy Prometheus alerts for OpenBao lease expiration (<10 min), CNPG connection pool (>80%), MinIO storage (>80%), and Keycloak auth failures (>5/min) (no approval required)
14. Implement Keycloak rate limiting (max 5 failed attempts/min per service account) (no approval required)
15. Conduct post-incident review and update runbooks for secret management failures (no approval required)

## ATLAS Techniques Observed

| Technique ID | Name | Evidence |
|--------------|------|----------|
| AML.T0010 | Credential Access | OpenBao lease expiration exposed authentication tokens; 4 consecutive renewal failures for accessor-abc123; Keycloak token refresh failures |
| AML.T0010.001 | Brute Force | 3 consecutive authentication failures from service account svc-aiops-sec-agent (IP: 10.0.1.45) within 7 seconds |
| AML.T0034 | Resource Hijacking | aiops-sec-agent pod crash loop (5 restarts) caused denial of service to AI/ML security monitoring for 4m 15s |
| AML.T0029 | Denial of ML Service | Database connection exhaustion (100/100), MinIO storage quota breach (95%), Kafka consumer disconnection - all preventing ML pipeline execution |
| AML.T0040 | ML Supply Chain Compromise | Spark log aggregation job failure disrupted security event correlation pipeline; potential blind spot in threat intelligence |

**Classification:** No evidence of malicious activity detected. All failures traced to operational misconfiguration (VSO auto-renewal failure). Service mesh mTLS integrity maintained throughout incident.