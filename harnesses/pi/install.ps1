$ErrorActionPreference = 'Stop'
$KitRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
$Python = if ($env:PYTHON) { $env:PYTHON } else { 'python' }
& $Python (Join-Path $KitRoot 'scripts/install-kit.py') @args
exit $LASTEXITCODE
