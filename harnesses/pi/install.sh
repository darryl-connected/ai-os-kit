#!/bin/bash
# =============================================================================
# pi install — wire the AIS-OS Kit to the pi coding agent
# =============================================================================
# Run from the kit root after unzipping:
#   bash harnesses/pi/install.sh
#
# What this does:
#   1. Copies skills/ → .pi/skills/ at the vault root
#   2. Copies templates/OPERATIONS.md → AGENTS.md at the vault root
#   3. Prints instructions for the global identity layer (APPEND_SYSTEM.md)
#
# Idempotent: re-run after pulling kit updates.
# =============================================================================

set -e

# Resolve vault root (parent of harnesses/pi/)
VAULT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
KIT_ROOT="$VAULT_ROOT"
SKILLS_SRC="$KIT_ROOT/skills"
PI_SKILLS="$VAULT_ROOT/.pi/skills"

echo "AIS-OS Kit → pi install"
echo "Vault root: $VAULT_ROOT"
echo ""

# --- Step 1: skills ---
echo "[1/3] Installing skills to $PI_SKILLS ..."
mkdir -p "$PI_SKILLS"

if [ -z "$(ls -A "$SKILLS_SRC" 2>/dev/null)" ]; then
  echo "  ! No skills found in $SKILLS_SRC — kit may be incomplete."
  exit 1
fi

INSTALLED=0
for skill_dir in "$SKILLS_SRC"/*/; do
  skill_name=$(basename "$skill_dir")
  cp -r "$skill_dir" "$PI_SKILLS/$skill_name"
  echo "  + $skill_name"
  INSTALLED=$((INSTALLED + 1))
done

echo "  $INSTALLED skills installed."
echo ""

# --- Step 2: operations layer (AGENTS.md) ---
echo "[2/3] Installing vault operations layer (AGENTS.md) ..."
if [ -f "$VAULT_ROOT/AGENTS.md" ]; then
  echo "  ! AGENTS.md already exists at vault root."
  echo "    Leaving it alone — back it up and copy templates/OPERATIONS.md manually if you want a fresh start."
else
  cp "$KIT_ROOT/templates/OPERATIONS.md" "$VAULT_ROOT/AGENTS.md"
  echo "  + AGENTS.md created at vault root."
  echo "  >> Edit it: replace {{Your Name}} with your actual name."
fi
echo ""

# --- Step 3: identity layer instructions ---
echo "[3/3] Identity layer (global) — MANUAL STEP"
echo ""
echo "  pi loads a global APPEND_SYSTEM.md (typically at ~/.pi/agent/APPEND_SYSTEM.md)."
echo "  Copy templates/IDENTITY.md content into that file, fill in your details."
echo ""
echo "  Quick check for the current location:"
echo "    ls ~/.pi/agent/ 2>/dev/null && echo 'found' || echo 'not found — check pi docs'"
echo ""

echo "Done. Next steps:"
echo "  1. Edit $VAULT_ROOT/AGENTS.md (replace {{Your Name}} etc.)"
echo "  2. Copy templates/IDENTITY.md → your global APPEND_SYSTEM.md location"
echo "  3. Open the vault in pi and run /onboard"
echo "  4. Day 7: run /audit"