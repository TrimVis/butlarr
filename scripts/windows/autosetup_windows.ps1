$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
. "$scriptPath\common_windows.ps1"

Find-RepoRoot
Open-Venv

Write-Host " |> Starting butlarr autosetup"
python -m butlarr.autosetup
