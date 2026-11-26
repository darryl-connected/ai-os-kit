# Fathom: recent recordings

## Setup and scoped check

Use a Fathom API key from your Fathom settings. Set `FATHOM_API_KEY` locally as described in the [credential guide](../README.md#optional-connections). Fathom uses `X-Api-Key`. The connector never asks for a ClickUp token. Record the intended recording or recent-feed scope and local filing folders in [connections.md](../connections.md).

```bash
python scripts/fathom-fetch.py --check
```

This makes a real GET of the recent feed with content fields disabled and writes nothing. A valid empty feed is still a successful read. To check for a specific recording, add `--share-url` and a suitable `--limit`; it will report if the link is outside the scanned window or not visible. This does not prove broader sharing permissions. Missing configuration, rejected auth/scope, and a successful scoped read are distinct. No error prints headers, response bodies or token values.

## Fetch when asked

```bash
python scripts/fathom-fetch.py
python scripts/fathom-fetch.py --backfill --limit 15
```

Default: scan up to 10 recent recordings, saving the **newest unfiled recording** in that window. Backfill writes every unfiled recording in the scanned window, up to 30 by default. Neither mode retrieves all history. `--limit` is a positive total scan depth, not a requested API page size. Pair `--share-url` with a scan when the user wants only a specific recording. The listing may return neighbouring recordings before the local filter runs; use a supplied export if reading that feed is outside scope. `--vault` optionally selects a different local vault.

The script calls `GET https://api.fathom.ai/external/v1/meetings`, includes summaries, action items and transcripts when fetching, and follows `next_cursor`. It stops at the total depth or end of feed and errors on a repeated cursor. Recordings without a usable share URL are skipped. It compares exact URLs in the inbox, processed captures and every registered project `meetings/` folder. The readable filename uses a stable share-URL hash so equal dates/titles do not replace one another.

Next: run `/skill:meeting-intake` in Pi to review and file the capture. Fetching alone does not approve local filing or any remote task write.

For API changes, consult [Fathom's developer documentation](https://developers.fathom.ai/). A fixture or documentation lookup does not verify your account, its accessible recordings or the current service response.
