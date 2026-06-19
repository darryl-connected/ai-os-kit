---
name: gameplan
description: 'Build a tight daily game plan by synthesizing the current focus file, priorities, calendar (with response status), and inbox. Triggers on "game plan", "what''s my plan for today", "morning plan", "what should I do today", "plan my day". Output: 3-5 bullets, time-anchored, with explicit gaps and waiting-on-others callouts. NOT a weekly retrospective (use level-up), NOT a PM report (build weekly-exec-brief separately), NOT a structural audit (use audit).'
---

## What this skill does

Pulls live data from the AIOS (focus, priorities, calendar, inbox) and synthesizes a tight 3-5 bullet game plan for the day. Designed to run in 2-3 minutes. Output is time-anchored and honest about what's open, what's blocked, and what just opened up.

The Default Shift applies — if a step is repetitive, flag it for `/level-up`.

## When to use

- Morning ritual (start of day)
- "What's on today" mid-day reset
- After a meeting ends, to re-plan the rest of the day

## When NOT to use

- Weekly retrospective / opportunity finding → `/level-up`
- Structural AIOS audit → `/audit`
- PM-level weekly report → build `weekly-exec-brief` skill (separate concern, this kit ships the pattern but not the skill itself)
- Looking at last week → check `projects/<project>/_current.md` and `decisions/log.md` directly
- Single-task planning → just do it, no skill needed

## Inputs the skill reads

In this order. Each pull is one tool call. Don't fetch what you don't need.

1. **System date** — `python -c "import datetime; print(datetime.datetime.now().strftime('%A %Y-%m-%d %H:%M:%S'))"`. **Never infer the day of the week from memory.** Always render both date and day.
2. **Focus file** — `projects/<project>/_current.md`. If multiple projects exist, ask which one. If only one active project, assume it.
3. **Priorities** — `context/priorities.md`. Top 3 quarter-level goals.
4. **Calendar, next 3 days** — via `scripts/google_calendar_api.py events --days 3 --max 30 --verbose`. For each event capture:
   - Start **and** end (always render both; `list_events` does not auto-render end)
   - Title
   - **Response status** (accepted / declined / tentative / needsAction) — checked via the `attendees[].self.responseStatus` field, not by the event's existence
   - Organizer
5. **Inbox** — via direct `get_gmail_service()` call. Two passes:
   - `is:unread newer_than:2d` — what needs attention now
   - `from:<key-person> newer_than:14d` — last contact with the people named in `_current.md` "Blockers" / "Next actions" sections
6. **Decisions log** (last 5 entries) — `decisions/log.md`. Recent commitments that might still be open.

## Execution

### Step 0: Pre-flight checks (silent)

- Confirm Gmail + Calendar scripts work. On Windows, Python's default `cp1252` stdout can crash with "I/O operation on closed file" when printing emoji or non-ASCII — use `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` at the top of any script that prints ✓/❌/etc.
- If `inbox/` has unprocessed Fathom dumps, mention it once and keep moving.

### Step 1: Pull and render calendar (be honest about time)

For every event, render exactly this shape:

```
HH:MM–HH:MM  Title                          [STATUS]
  org: <organizer>
```

Status values: ✅ accepted · ❌ declined · ❔ tentative · ⏳ needsAction.

Compute free blocks between accepted events. Always end the calendar summary with:

```
Open blocks today: HH:MM–HH:MM (Xh Ym)
```

This is the most important line. It tells the user where the work goes.

### Step 2: Inbox triage (top 5 only)

Sort by recency. Highlight anything from a person named in `_current.md` "Blockers" or "Next actions" sections. If a recent email suggests a blocker is now unblocked (or newly blocked), call it out explicitly.

### Step 3: Synthesize the plan

Output a tight 3-5 bullets, in this priority order:

1. **Time-anchored commitment** — the most important thing for today, with the time slot. Example: "10:00–12:00 Discovery call — surface the 3 blocked items in person."
2. **The biggest open block** — the largest free window, with the best-fit task. Match the task to the priorities in `context/priorities.md`.
3. **One fast admin item** — inbox reply, ping, follow-up, scratch triage. Pick the one with highest leverage and lowest effort (≤15 min).
4. **Drop from today** — explicit. What was on the focus file but doesn't fit. Don't be timid about this.
5. **Waiting on others** — bullet list. Items the user cannot move forward on. Don't suggest working on these.

Rules:
- **3-5 bullets, not more.** Cut before you go over.
- **Every bullet has a time or a duration.** No floating tasks.
- **Be specific, not generic.** "Skim Figma design system" beats "review documents."
- **If you got something wrong, say so.** Self-correct in line, don't bury it.

### Step 4: Close

One line: confirmation of what was pulled and any tool errors that came up. If the calendar API was used and the response was clean, say "calendar clean" — gives the user a heartbeat that data is fresh.

## Edge cases

| Situation | What to do |
|---|---|
| `_current.md` doesn't exist for the active project | Ask which project, then read its README as fallback. |
| Calendar is empty | Plan is just priorities + inbox-driven. Lead with the biggest focus-file action. |
| Inbox returns 0 unread | Note "(inbox clean)" and move on. Don't fabricate. |
| Gmail script crashes with "I/O operation on closed file" | Switch to `python -c "from google_auth import get_gmail_service; ..."` direct call. Don't fix the script mid-run. |
| Multiple projects in flight | Ask which one to plan around before pulling. |
| Today is a holiday / weekend | Ask whether to plan for today or Monday. |
| Fathom meeting from yesterday has open action items | Surface them as today's #1 candidate. |
| A meeting was declined but is still on the calendar | It's still on the calendar. Show it. Let the user see it and re-confirm. |
| No calendar script wired yet | Suggest wiring `scripts/google_calendar_api.py` per `scripts/README.md`. Skip calendar in this run, lead with priorities. |

## What this skill will NOT do

- **Reschedule meetings.** No calendar writes. Use `google_calendar_api.py update` directly with `--yes`.
- **Send emails.** No Gmail writes. Drafts go in the response; user sends.
- **Re-run the focus-file weekly review.** That's a Friday ritual, not a daily plan.
- **Build a weekly report.** That's a separate PM-reporting skill (this kit ships the pattern but not the skill itself).
- **Auto-archive inbox.** Out of scope.
- **Optimize for "more bullets."** Tight is the goal. 3-5 only.

## Output contract

Every run produces:
1. Calendar block (Step 1)
2. Inbox signal (Step 2)
3. 3-5 bullet plan (Step 3)
4. One-line close (Step 4)

Effort target: 2-3 min runtime. If it's running longer, the pull phase is wrong — too much data, not enough filtering.

## Notes

- The skill is Bike Method Phase 1 (manual trigger). Don't auto-run on session start.
- If a tool returns data the user disagrees with, fix the upstream source (calendar event, focus file, etc.) — don't patch around it in the response.
- The "Open blocks today" line is the highest-leverage part of the output. If only one line makes it through, that's the one.
- This skill is the daily counterpart to `/level-up` (weekly opportunity) and any weekly PM-reporting skill (weekly/monthly cadence).