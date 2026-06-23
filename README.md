# aiops-sec-agent

A LangGraph multi-agent system for OT/ICS security operations. Correlates logs across 9 platform sources, triages alerts with MITRE ATLAS technique tagging, and generates structured incident reports using Claude AI as the reasoning engine.

## Architecture

Four specialized agents orchestrated by a supervisor graph:

- **log_correlation_agent** — Ingests logs from Istio, Keycloak, ArgoCD, Kubernetes, OpenBao, Kafka, MinIO, CloudNativePG, and Spark; joins across sources using DuckDB SQL
- **alert_triage_agent** — Classifies alerts by severity, maps to MITRE ATLAS techniques (AML.T0010, T0029, T0034, T0040), distinguishes operational failures from adversarial activity
- **remediation_agent** — Generates tiered remediation actions (immediate / short-term / config changes / monitoring) with human-approval gates for sensitive operations
- **supervisor** — LangGraph StateGraph orchestrator; routes between agents and compiles the final report

## Stack

| Layer | Technology |
|-------|-----------|
| Agent framework | LangGraph 1.x |
| Reasoning engine | Anthropic Claude (claude-sonnet-4-6) |
| Log correlation | DuckDB |
| MCP servers | kubectl, ArgoCD, log-query (Docker Compose) |
| Platform sources | Istio · Keycloak · ArgoCD · K8s · OpenBao · Kafka · MinIO · CNPG · Spark |

## Threat Coverage (MITRE ATLAS)

| Technique | Name |
|-----------|------|
| AML.T0010 | Credential Access |
| AML.T0010.001 | Brute Force |
| AML.T0029 | Denial of ML Service |
| AML.T0034 | Resource Hijacking |
| AML.T0040 | ML Supply Chain Compromise |

## Quickstart

```bash
git clone https://github.com/Sharatmenon/aiops-sec-agent.git
cd aiops-sec-agent
python3.11 -m venv .venv311 && source .venv311/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your ANTHROPIC_API_KEY
python3 main.py --output report.md
```

## Sample Output

The agent produces a structured incident report including:
- Executive summary with root cause
- Full event timeline with UTC timestamps
- Alert list with MITRE ATLAS tags and severity ratings
- Current platform state (pods, ArgoCD apps, infrastructure)
- Tiered remediation actions with human-approval gates

See [`report.md`](report.md) for a full example output.

## MCP Servers (optional)

Three MCP servers are included for live cluster connectivity:

```bash
docker compose up -d
```

- **kubectl-mcp** — Pod health and cluster state
- **argocd-mcp** — GitOps sync status
- **logquery-mcp** — Structured log queries

Swap stub tools for MCP tools in `tools.py` when connecting to a live cluster.

## Use Case

Built as a portfolio demonstration of AI-powered security operations for OT/ICS environments. The same pattern applies to any cloud-native platform running Kubernetes workloads — swap the log sources in `logs/` and update DuckDB queries in `db.py` to adapt.

## License

MIT
