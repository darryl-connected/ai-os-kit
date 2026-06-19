---
type: spec
status: active
date: 2026-06-15
topic: [metrics]
priority: workflow
---

# Habit Tracker — v1 Feature Spec

## Summary

A mobile app that helps working professionals build daily habits through a low-friction check-in experience and streak visualization. No social features in v1. Local storage for Sprint 1, backend from Sprint 2.

## User stories

### P0 (Must ship in v1)

- **As a new user**, I can create a habit by entering a name, picking a frequency (daily, weekdays, custom), and choosing a time-of-day.
- **As a user**, I see today's habits on launch and can confirm completion with one tap.
- **As a user**, I see my current streak for each habit and my best streak ever.
- **As a user**, I receive a weekly summary notification every Sunday at 8pm local time.

### P1 (Nice to have for v1)

- **As a user**, I can edit or delete a habit.
- **As a user**, I get a streak freeze token per month (automatic, no opt-in).
- **As a user**, I see a calendar heatmap of completed days.

### Out of scope (deferred to v2+)

- Social features (friends, accountability)
- Apple Health / Google Fit integrations
- Premium tier / monetization
- Web version
- Habit stacking, correlation analytics

## Success metrics

| Metric | Target | How measured |
|---|---|---|
| D30 retention | > 25% | Analytics: cohort analysis |
| DAU/MAU | > 20% | Analytics: daily/monthly active |
| App Store rating | > 4.5 | App Store Connect |
| NPS | > 40 | In-app survey (P1) |

## Technical constraints

- iOS first (Sprint 1-3), Android via React Native (post-v1)
- Local storage in Sprint 1 (CoreData or SQLite)
- Backend from Sprint 2 (Postgres + REST API)
- Push notifications via APNs (Sprint 2)
- No analytics SDK in Sprint 1; add in Sprint 2 (privacy-first: PostHog self-hosted)

## Sprint breakdown

| Sprint | Scope | Duration |
|---|---|---|
| Sprint 1 | Habit creation + daily check-in | 2 weeks |
| Sprint 2 | Streak viz + weekly notification + backend | 2 weeks |
| Sprint 3 | Onboarding + polish + TestFlight + App Store | 2 weeks |

## Open questions

- Notification permission UX (research needed in Sprint 2)
- Streak freeze: 1/month free vs. paid tier
- Onboarding flow length (Carol designing in Sprint 1)

---

## Related
- **Topics:** [[metrics]], [[user-research]]
- **Source meeting:** [[2026-06-15 - discovery-call]]
- **Related notes:** [[2026-06-17 - planning-sync]], [[2026-06-18 - retro]]