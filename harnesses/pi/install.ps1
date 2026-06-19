# =============================================================================
# pi install (Windows PowerShell) — wire the AIS-OS Kit to pi
# =============================================================================
# Run from the kit root after unzipping:
#   powershell -ExecutionPolicy Bypass -File harnesses/pi/install.ps1
#
# What this does:
#   1. Copies skills/ -> .pi/skills/ at the vault root
#   2. Copies templates/OPERATIONS.md -> AGENTS.md at the vault root
#   3. Prints instructions for the global identity layer (APPEND_SYSTEM.md)
#
# Idempotent: re-run after pulling kit updates.
# =============================================================================

$ErrorActionPreference = "Stop"

# Resolve vault root (parent of harnesses/pi/)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VaultRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)
$KitRoot = $VaultRoot
$SkillsSrc = Join-Path $KitRoot "skills"
$PiSkills = Join-Path $VaultRoot ".pi/skills"

Write-Host "AIS-OS Kit -> pi install (PowerShell)"
Write-Host "Vault root: $VaultRoot"
Write-Host ""

# --- Step 1: skills ---
Write-Host "[1/3] Installing skills to $PiSkills ..."
if (-not (Test-Path $PiSkills)) {
  New-Item -ItemType Directory -Path $PiSkills | Out-Null
}

if (-not (Test-Path $SkillsSrc) -or -not (Get-ChildItem -Path $SkillsSrc -Directory)) {
  Write-Host "  ! No skills found in $SkillsSrc -- kit may be incomplete."
  exit 1
}

$Installed = 0
Get-ChildItem -Path $SkillsSrc -Directory | ForEach-Object {
  $SkillName = $_.Name
  $DestDir = Join-Path $PiSkills $SkillName
  if (Test-Path $DestDir) {
    Remove-Item -Recurse -Force $DestDir
  }
  Copy-Item -Recurse -Path $_.FullName -Destination $DestDir
  Write-Host "  + $SkillName"
  $Installed++
}
Write-Host "  $Installed skills installed."
Write-Host ""

# --- Step 2: operations layer (AGENTS.md) ---
Write-Host "[2/3] Installing vault operations layer (AGENTS.md) ..."
$AgentsPath = Join-Path $VaultRoot "AGENTS.md"
if (Test-Path $AgentsPath) {
  Write-Host "  ! AGENTS.md already exists at vault root."
  Write-Host "    Leaving it alone -- back it up and copy templates/OPERATIONS.md manually if you want a fresh start."
} else {
  $OpsTemplate = Join-Path $KitRoot "templates/OPERATIONS.md"
  Copy-Item -Path $OpsTemplate -Destination $AgentsPath
  Write-Host "  + AGENTS.md created at vault root."
  Write-Host "  >> Edit it: replace {{Your Name}} with your actual name."
}
Write-Host ""

# --- Step 3: identity layer instructions ---
Write-Host "[3/3] Identity layer (global) -- MANUAL STEP"
Write-Host ""
Write-Host "  pi loads a global APPEND_SYSTEM.md (typically at ~/.pi/agent/APPEND_SYSTEM.md)."
Write-Host "  Copy templates/IDENTITY.md content into that file, fill in your details."
Write-Host ""
Write-Host "  Quick check for the current location:"
Write-Host "    Test-Path ~/.pi/agent/APPEND_SYSTEM.md"
Write-Host ""

Write-Host "Done. Next steps:"
Write-Host "  1. Edit $AgentsPath (replace {{Your Name}} etc.)"
Write-Host "  2. Copy templates/IDENTITY.md -> your global APPEND_SYSTEM.md location"
Write-Host "  3. Open the vault in pi and run /onboard"
Write-Host "  4. Day 7: run /audit"