# Connection scope

Keep non-secret scope and observed access status here. Skip any connector not needed for the current task. Do not record keys, and do not mark access as checked unless the scoped read succeeded.

When agreed, record scope as a `Fathom scope:` or `ClickUp scope:` bullet. Onboarding can add these for you. A missing value means the scope has not been agreed.

Use `scripts/setup-kit.py --meeting-destination` to record a project meeting folder for Fathom deduplication. Each configured folder has one `Meeting destination:` bullet with a vault-relative `projects/<project-slug>/meetings` value (lowercase letters, digits, hyphens or underscores in the slug). There is no default project. Inbox and processed capture locations are fixed.

Connection scope records what the user permits the assistant to read. It is not a replacement for service permissions or a sandbox. Verify only the agreed scope using the [Fathom](references/fathom-api.md) or [ClickUp](references/clickup-api.md) reference. Dates, errors and what was checked can be noted here if useful.
