# =============================================================================
# Claude Code install (Windows PowerShell) — wire the AIS-OS Kit to Claude Code
# =============================================================================
# Run from the kit root after unzipping:
#   powershell -ExecutionPolicy Bypass -File harnesses/claude-code/install.ps1
#
# What this does:
#   1. Copies skills/ -> .claude/skills/ at the vault root
#   2. Confirms CLAUDE.md is at the vault root (already there from the kit)
#   3. Prints customization instructions
#
# Idempotent: re-run after pulling kit updates.
# =============================================================================

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VaultRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)
$KitRoot = $VaultRoot
$SkillsSrc = Join-Path $KitRoot "skills"
$ClaudeSkills = Join-Path $VaultRoot ".claude/skills"
$ClaudeMd = Join-Path $VaultRoot "CLAUDE.md"

Write-Host "AIS-OS Kit -> Claude Code install (PowerShell)"
Write-Host "Vault root: $VaultRoot"
Write-Host ""

# --- Step 1: skills ---
Write-Host "[1/3] Installing skills to $ClaudeSkills ..."
if (-not (Test-Path $ClaudeSkills)) {
  New-Item -ItemType Directory -Path $ClaudeSkills | Out-Null
}

if (-not (Test-Path $SkillsSrc) -or -not (Get-ChildItem -Path $SkillsSrc -Directory)) {
  Write-Host "  ! No skills found in $SkillsSrc -- kit may be incomplete."
  exit 1
}

$Installed = 0
Get-ChildItem -Path $SkillsSrc -Directory | ForEach-Object {
  $SkillName = $_.Name
  $DestDir = Join-Path $ClaudeSkills $SkillName
  if (Test-Path $DestDir) {
    Remove-Item -Recurse -Force $DestDir
  }
  Copy-Item -Recurse -Path $_.FullName -Destination $DestDir
  Write-Host "  + $SkillName"
  $Installed++
}
Write-Host "  $Installed skills installed."
Write-Host ""

# --- Step 2: CLAUDE.md ---
Write-Host "[2/3] Identity + operations layer (CLAUDE.md) ..."
if (Test-Path $ClaudeMd) {
  Write-Host "  v CLAUDE.md already exists at vault root."
  Write-Host "  >> Edit it: replace {{Your Name}} with your actual name."
  Write-Host "  >> Re-running this install won't overwrite your customizations."
} else {
  Write-Host "  ! CLAUDE.md missing. The kit ships one -- extracting from kit..."
  $KitClaudeMd = Join-Path $KitRoot "CLAUDE.md"
  if (Test-Path $KitClaudeMd) {
    Copy-Item -Path $KitClaudeMd -Destination $ClaudeMd
    Write-Host "  + CLAUDE.md created at vault root."
  } else {
    Write-Host "  !! Kit CLAUDE.md missing. Re-download the kit or copy manually."
    exit 1
  }
}
Write-Host ""

# --- Step 3: instructions ---
Write-Host "[3/3] Next steps"
Write-Host ""
Write-Host "  Claude Code uses a single CLAUDE.md file at the vault root."
Write-Host "  It contains BOTH the identity layer and the operations layer merged."
Write-Host "  No global config file needed (unlike pi)."
Write-Host ""

Write-Host "Done. Next steps:"
Write-Host "  1. Edit $ClaudeMd (replace {{Your Name}} etc.)"
Write-Host "  2. Open the vault in Claude Code and run /onboard"
Write-Host "  3. Day 7: run /audit"