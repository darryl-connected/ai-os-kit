# Build and verify the lean ZIP

This page is for the source checkout, not part of the shipped archive. The repo retains legacy connector, skill, framework and harness files. The supported distribution is Pi-only. Do not distribute a checkout or zip directories wholesale.

Build with `python scripts/build-kit.py` (or pass `--output` for a different ZIP). The build prints its inventory. `scripts/kit_files.py` lists the distributed defaults, and `tests/acceptance_package.py` has a separate expected inventory. For release candidates, test an actual extracted archive rather than running only against the checkout.

Use Python 3.11+ in a virtual environment with `requirements-dev.txt`. Skill and package checks also need Node.js and a local Pi SDK installation. Set `PI_DIST` when the Pi module directory cannot be inferred from the executable. No service tokens or model calls are needed.

| Command | Checks |
|---|---|
| `python scripts/check-kit.py typecheck` | Strict mypy on the distributed Python runtime and build/check entrypoints. |
| `python scripts/check-kit.py lint` | Ruff, shell syntax, and both shipped skills through Pi's loader. |
| `python scripts/check-kit.py unit` | Fathom cursor, bounds and dedup; ClickUp scoped reads and preview/approval with HTTP transport replaced. |
| `python scripts/check-kit.py build` | ZIP generation, inventory and checksums. Set `KIT_BUILD_OUTPUT` to keep the artifact outside the checkout. |
| `python scripts/check-kit.py acceptance` | Actual setup and filing in temporary vaults; credential state and precedence with fake replies; native Pi installs and updates; archive resources, resolved local links and documented slash commands against Pi's offline command surface. |

The offline checks do not validate live authentication, account permissions, current API compatibility or LLM adherence. Bash and PowerShell adapters require separate native runs; an unavailable platform is not verified.
