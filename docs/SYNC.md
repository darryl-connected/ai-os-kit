# Update, migrate or sync your vault

Always extract a new kit archive into a **separate folder**. Unzipping over a working vault can overwrite files before the adapter has a chance to protect them.

## Use an existing vault

From the newly extracted kit, run the Pi adapter with `--vault` and the path to your existing vault:

```bash
bash harnesses/pi/install.sh --vault "$HOME/work notes"
```

On Windows use the corresponding `.ps1` adapter, for example `powershell -File harnesses/pi/install.ps1 --vault 'C:\Work Notes'`. The adapter copies missing kit files and reports existing paths or symlinks it skipped. Use the same extracted source for reruns. It does not replace profile facts, `.env`, connection status, project files, rules, custom skills or global configuration. It does not remove any files.

Review the reported conflicts before using an updated vault. Compare older shipped connectors, instructions and skills with the new archive and adopt the changes you want explicitly. Old rule files may still mention obsolete flows; merge the relevant rules rather than replacing your own. Old extra skills may still be discoverable; disable or move an old kit skill yourself only after checking for personal changes. The installer cannot determine whether an existing file with a familiar name is yours to keep. If you would rather not merge, start in a fresh kit folder and bring over chosen personal notes, rules and skills deliberately.

Keep stable facts in `context/about-me.md`, connector scope in `connections.md`, and project facts with the project. If an old intake contains the only copy of a relevant fact, confirm it and move that fact manually. Don't replay old intake or copy it into new rules. Older structured scope syntax can be added to the existing registry without discarding prior status notes; see [connections.md](../connections.md). Credentials are configured per machine only if needed.

## Sync or back up intentionally

- Exclude `.env`, connector credentials, harness auth and sensitive capture folders unless you have explicitly chosen a suitable protected storage policy. `.gitignore` does not exclude files from cloud sync, sharing or backups.
- [Processed captures](../inbox/processed/README.md) contain full original notes or transcripts until you explicitly clean them up. Check storage and who can access the content before syncing.
- On a second device, install the Pi adapter in the working vault, add only the local credentials you need, and check the agreed source scope. Avoid simultaneous edits or reconcile conflict copies manually. Do not sync another user's global configuration.

See the [quick start](../README.md) and [connector commands](../scripts/README.md).
