$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
. "$scriptPath\common_windows.ps1"

Find-RepoRoot
Open-Venv

# Finally start bot
Write-Host " |> Starting butlarr"
python -m butlarr
