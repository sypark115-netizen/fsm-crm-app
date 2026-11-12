# Install proposal-red-team for Claude Code and/or Codex on Windows (local copy only).
#   powershell -ExecutionPolicy Bypass -File .\install.ps1            # both
#   powershell -ExecutionPolicy Bypass -File .\install.ps1 claude
#   powershell -ExecutionPolicy Bypass -File .\install.ps1 codex
param([ValidateSet("both", "claude", "codex")][string]$Target = "both")
$ErrorActionPreference = "Stop"
$src = $PSScriptRoot

function Copy-Skill($root) {
    $dest = Join-Path $root "proposal-red-team"
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    robocopy $src $dest /MIR /XD evals tests __pycache__ .pytest_cache .git /NFL /NDL /NJH /NJS | Out-Null
    Write-Host "installed -> $dest"
}

$codexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME ".codex" }
if ($Target -in "both", "claude") { Copy-Skill (Join-Path $HOME ".claude\skills") }
if ($Target -in "both", "codex")  { Copy-Skill (Join-Path $codexHome "skills") }

$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command py -ErrorAction SilentlyContinue }  # Windows PowerShell 5.1 has no ?? operator
if ($py) { & $py.Source -m pip install -q -r (Join-Path $src "scripts\requirements.txt") }
else { Write-Warning "Python not found - install Python 3.10+ and run: pip install -r scripts\requirements.txt" }

if (-not (Get-Command soffice -ErrorAction SilentlyContinue)) {
    Write-Host "note: LibreOffice (soffice) not on PATH - export decks to PDF next to the PPTX, or add 'C:\Program Files\LibreOffice\program' to PATH"
}
