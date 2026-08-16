---
name: ai-subscription-usage
description: Generate and explain a local offline usage report for Codex, Claude Code, Gemini CLI, and Grok Build.
---

# AI Subscription Usage

Use this skill when the user asks for a local AI subscription token report, daily model usage, API-equivalent cost, subscription comparison, or local provider detection.

Run the bundled report script with Python 3. It only reads local session records and writes a static HTML report. It does not start a server, access the network, read credentials, or upload data.

```bash
python3 src/ai_usage_report.py --days 30
```

The output is `outputs/ai-usage-report.html`. Explain each provider's source fidelity: Codex and Claude Code contain token records; Gemini CLI uses its local chat records when present; Grok Build supplies a context-token estimate only, not a billable input/output ledger.

Do not alter `config/pricing.json` without the user's explicit approval. Its values must come from official provider documentation, and an unknown model must remain unpriced.
