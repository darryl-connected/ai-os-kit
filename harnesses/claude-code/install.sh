#!/bin/bash
# =============================================================================
# Claude Code install — wire the AIS-OS Kit to Claude Code
# =============================================================================
# Run from the kit root after unzipping:
#   bash harnesses/claude-code/install.sh
#
# What this does:
#   1. Copies skills/ → .claude/skills/ at the vault root
#   2. Confirms CLAUDE.md is at the vault root (already there from the kit)
#   3. Prints customization instructions
#
# Idempotent: re-run after pulling kit updates.
# =============================================================================

set -e

VAULT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
KIT_ROOT="$VAULT_ROOT"
SKILLS_SRC="$KIT_ROOT/skills"
CLAUDE_SKILLS="$VAULT_ROOT/.claude/skills"
CLAUDE_MD="$VAULT_ROOT/CLAUDE.md"

echo "AIS-OS Kit → Claude Code install"
echo "Vault root: $VAULT_ROOT"
echo ""

# --- Step 1: skills ---
echo "[1/3] Installing skills to $CLAUDE_SKILLS ..."
mkdir -p "$CLAUDE_SKILLS"

if [ -z "$(ls -A "$SKILLS_SRC" 2>/dev/null)" ]; then
  echo "  ! No skills found in $SKILLS_SRC — kit may be incomplete."
  exit 1
fi

INSTALLED=0
for skill_dir in "$SKILLS_SRC"/*/; do
  skill_name=$(basename "$skill_dir")
  cp -r "$skill_dir" "$CLAUDE_SKILLS/$skill_name"
  echo "  + $skill_name"
  INSTALLED=$((INSTALLED + 1))
done

echo "  $INSTALLED skills installed."
echo ""

# --- Step 2: CLAUDE.md ---
echo "[2/3] Identity + operations layer (CLAUDE.md) ..."
if [ -f "$CLAUDE_MD" ]; then
  echo "  ✓ CLAUDE.md already exists at vault root."
  echo "  >> Edit it: replace {{Your Name}} with your actual name."
  echo "  >> Re-running this install won't overwrite your customizations."
else
  echo "  ! CLAUDE.md missing. The kit ships one — extracting from kit..."
  if [ -f "$KIT_ROOT/CLAUDE.md" ]; then
    cp "$KIT_ROOT/CLAUDE.md" "$CLAUDE_MD"
    echo "  + CLAUDE.md created at vault root."
  else
    echo "  !! Kit CLAUDE.md missing. Re-download the kit or copy manually."
    exit 1
  fi
fi
echo ""

# --- Step 3: instructions ---
echo "[3/3] Next steps"
echo ""
echo "  Claude Code uses a single CLAUDE.md file at the vault root."
echo "  It contains BOTH the identity layer and the operations layer merged."
echo "  No global config file needed (unlike pi)."
echo ""

echo "Done. Next steps:"
echo "  1. Edit $CLAUDE_MD (replace {{Your Name}} etc.)"
echo "  2. Open the vault in Claude Code and run /onboard"
echo "  3. Day 7: run /audit"