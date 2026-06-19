---
type: meeting
status: active
date: 2026-06-17
topic: [metrics]
priority: workflow
recording: https://fathom.video/share/demo-planning-sync
attendees: [Alice, Bob, Carol]
---

[**VIEW RECORDING - 60 mins**](https://fathom.video/share/demo-planning-sync)

## Meeting Purpose

Sprint planning for Habit Tracker v1. Lock the first sprint scope and assign work.

## Key Takeaways

- **Sprint 1 (2 weeks):** habit creation + daily check-in. Ship behind a feature flag, dogfood internally.
- **Sprint 2:** streak visualization + weekly summary notification.
- **Sprint 3:** polish, onboarding flow, app store assets.
- **Launch target:** end of July (TestFlight first, App Store submission early August).

## Topics

### Sprint 1 scope

- Habit creation screen (name, frequency picker, time-of-day)
- Local storage (no backend in Sprint 1)
- Daily check-in screen (one-tap confirm, current streak shown)
- Feature flag system for staged rollout

### Sprint 2 scope

- Streak visualization (current, best, calendar heatmap)
- Weekly summary notification (Sunday 8pm local time)
- Persistence layer (move from local to backend)

### Sprint 3 scope

- Onboarding flow (3 screens max)
- App icon + screenshots for store listing
- TestFlight beta to internal team
- App Store submission prep

### Risks

- **Notification permissions:** iOS requires explicit opt-in. If users decline, weekly summary is dead. Mitigate with in-app prompts at strategic moments.
- **Streak anxiety:** users may delete habits to reset broken streaks. Mitigate with "freeze" tokens (1 per month, free).

## Next Steps

- **Bob:** Break down Sprint 1 into ClickUp tickets by end of week.
- **Alice:** Write Sprint 1 release notes template.
- **Carol:** Finalize onboarding screen designs by 2026-06-19.

---

## Related
- **Topics:** [[metrics]]
- **Series:** ← [[2026-06-15 - discovery-call]] | → [[2026-06-18 - retro]]
- **Decisions mentioned:**
  - Sprint 1 scope: habit creation + daily check-in
  - Launch target: end of July (TestFlight), early August (App Store)
  - Streak freeze tokens: 1 per month, free
- **Related notes:** [[2026-06-15 - feature-spec]], [[user-research]]