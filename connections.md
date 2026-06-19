# Connections

Registry of every system your AIOS can reach. Fill this in via `/onboard` (Q4–Q7), or update manually when you wire a new tool.

## Tier-1 Universal Data Domains

| # | Domain | Tool(s) | Mechanism | Auth | Last checked |
|---|---|---|---|---|---|
| 1 | Revenue / Financials |  |  |  |  |
| 2 | Customer interactions |  |  |  |  |
| 3 | Calendar |  |  |  |  |
| 4 | Communication (email/Slack/etc.) |  |  |  |  |
| 5 | Project / task tracking |  |  |  |  |
| 6 | Meeting intelligence |  |  |  |  |
| 7 | Knowledge / files |  |  |  |  |

**Mechanism values:** `MCP`, `api-script`, `export-pipeline`, `not yet connected`.

## Tier-2 (bonus)

| Tool | Purpose | Mechanism | Auth | Last checked |
|---|---|---|---|---|
|  |  |  |  |  |

## Per-connection reference notes

Each wired tool should have a research note in `references/{tool}-api.md`. Lint (Day 7) checks that connected tools have a corresponding reference; missing reference = -1 point per tool.

---

> **How to update:** when you wire a new tool, fill its row above AND write `references/{tool}-api.md` (endpoints, auth, common queries, known limitations). Re-run `/audit` to see the score climb.