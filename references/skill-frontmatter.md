# Skill frontmatter

Use a directory with a matching `SKILL.md` and a single-quoted description. The description says what the skill does and when to use it. Double any embedded single quote (`''`).

```yaml
---
name: my-skill
description: 'Review supplied notes and propose next steps.'
---
```

Names should be lowercase letters, numbers, and hyphens, with no leading, trailing, or consecutive hyphens. Names are at most 64 characters and descriptions at most 1024.

Run the actual Pi loader plus local style validation. Use Node.js and a local Pi installation; if the executable does not expose its module path, set `PI_DIST` to the Pi `dist` directory containing `core/skills.js`. No model or credentials are needed. Missing loader or invalid skills return a non-zero exit.

```bash
python scripts/lint-skills.py --skills-dir skills --strict
python scripts/lint-skills.py --skills-dir .pi/skills --skill onboard --strict
```

The kit defaults are `onboard` and `meeting-intake`. This command can also check custom skills after installation. See the [Pi skill docs](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/skills.md) for the loader rules.
