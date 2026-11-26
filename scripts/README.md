# Local commands

Run from the vault root with Python 3.11+. The default vault is the folder containing these scripts. Commands that accept `--vault` can target another local vault; for ClickUp, put `--vault` before the subcommand. Use `--help` to see supported flags. It does not validate live credentials.

## One useful first task

The local setup helper has no connector dependencies. Ask only for items missing for this task:

```bash
python scripts/setup-kit.py --task 'Draft QA scenarios' --sources supplied --material scratch/requirements.md
python scripts/setup-kit.py --task 'Review the planning capture' --sources fathom
```

`--material` emits a source-labelled brief and outline. The assistant drafts the actual deliverable from that material. It can do that even with incomplete profile fields. It does not check any live sources. Relevant profile and scope fields can be provided in the same invocation. After reviewing new facts, add `--save` to append them without overwriting old values:

```bash
python scripts/setup-kit.py --sources fathom --task 'Review the planning capture' \
  --fathom-scope 'Approved product planning recordings' \
  --meeting-destination projects/mobile-app/meetings --save
```

`--role`, `--team`, `--project`, and `--clickup-scope` can save further confirmed non-secret context. Existing structured values are not replaced; edit them in their authoritative files after review. Pass only new facts when saving; do not repeat facts already written in prose. The task and supplied material are not written to the profile. You can repeat `--meeting-destination` to register several real project folders.

## File a meeting locally

Place a full original in `inbox/` and a separate reviewed summary in `scratch/`. Check [meeting intake](../inbox/README.md) before filing. Example paths are for files you create:

```bash
python scripts/file-meeting.py --capture 'inbox/2026-06-17 - planning.md' \
  --draft scratch/planning-summary.md --destination projects/mobile-app/meetings --date 2026-06-17
```

Show the exact preview. After local approval, rerun the same command unchanged with `--apply`. It retains the original under `inbox/processed/` and links to it from the permanent summary. No same-name file with different bytes is replaced; choose another filename with the owner if there is a conflict. No remote writes or age-based cleanup occur.

## Work-data commands

- [Fathom](../references/fathom-api.md): scoped read diagnostic and bounded fetch into the inbox.
- [ClickUp](../references/clickup-api.md): scoped reads and separately approved writes.

For connector dependencies and credential handling, see the [setup guide](../README.md#optional-connections). No helper reads a token for an unrelated workflow.

## Skill validation

Use `python scripts/lint-skills.py --skills-dir skills --strict` to lint both shipped skills before editing or sharing them. See the [skill standard](../references/skill-frontmatter.md) for actual Pi loader validation and how to point at a local installation.
