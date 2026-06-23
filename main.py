"""
main.py — Entry point for aiops-sec-agent LangGraph multi-agent system.

Usage:
  python main.py                          # stub mode, no Docker needed
  USE_MCP_TOOLS=true python main.py       # MCP mode, requires docker compose up
  python main.py --output report.md       # save report to file
  python main.py --prompt "focus on..."   # custom prompt
"""

import os, sys, argparse
from dotenv import load_dotenv

load_dotenv()

if not os.environ.get("ANTHROPIC_API_KEY"):
    print("ERROR: ANTHROPIC_API_KEY not set. Copy .env.example to .env and add your key.")
    sys.exit(1)

from langchain_core.messages import HumanMessage
from graph import graph

DEFAULT_PROMPT = (
    "Analyze the platform logs for the current incident window. "
    "Identify all error patterns, correlate events across log sources to find causal chains, "
    "triage alerts by severity with MITRE ATLAS tags where applicable, "
    "check current pod and ArgoCD app health, "
    "and produce a structured incident report with recommended remediation actions."
)

def main():
    parser = argparse.ArgumentParser(description="aiops-sec-agent — LangGraph multi-agent security log analysis")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT, help="Analysis prompt")
    parser.add_argument("--output", default=None, help="Save report to file")
    args = parser.parse_args()

    mode = "MCP" if os.environ.get("USE_MCP_TOOLS", "false").lower() == "true" else "stub"
    print(f"\n{'='*60}")
    print(f"  aiops-sec-agent  |  mode: {mode}")
    print(f"{'='*60}")
    print(f"Prompt: {args.prompt[:80]}...")
    print()

    result = graph.invoke({
        "messages":     [HumanMessage(content=args.prompt)],
        "log_summary":  "",
        "alerts":       [],
        "pod_status":   "",
        "final_report": "",
    })

    report = result["final_report"]

    print(f"\n{'='*60}")
    print("  FINAL REPORT")
    print(f"{'='*60}\n")
    print(report)

    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
        print(f"\n[saved to {args.output}]")

if __name__ == "__main__":
    main()
