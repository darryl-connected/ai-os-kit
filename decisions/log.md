# Decisions Log

Append decisions that change future work, project scope, or a direction. Record why, not just what.

**Format per entry:**

```
## YYYY-MM-DD — Short title

**Decision:** what was decided.

**Why:** the reasoning, constraints, and what would change your mind.

**Alternatives considered:** what else was on the table.

**Owner:** who's accountable.
```

## 2026-11-26: Lean meetings and tasks kit

**Decision:** Start from one useful task. Keep optional Fathom and ClickUp, local `.env` or process credentials, and the two meeting/setup skills. File reviewed summaries separately from full original captures, retained until the owner explicitly chooses cleanup. Context7 is opt-in for documentation only.

**Why:** The kit should work from supplied material without setup rituals, keep project facts in one place and preserve the evidence behind meeting summaries.

**Alternatives considered:** Inline transcripts, a seven-day retention window, mandatory connection setup and a larger default connector bundle.

**Owner:** Darryl Lim.

## 2026-11-27: Pi-only distribution

**Decision:** Support Pi in the lean kit. Keep legacy adapter source out of the archive and leave users' existing files alone.

**Why:** Pi serves the current use case. Keeping one supported setup also keeps the documentation and installation checks aligned.

**Alternatives considered:** Keep two supported adapters and verify both session loaders.

**Owner:** Darryl Lim.