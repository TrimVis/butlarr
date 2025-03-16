function Find-RepoRoot {
    # Detect the repository root folder
    $maxDepth = 3
    while ($maxDepth -gt 0) {
        if (Test-Path ".git" -PathType Container) {
            break
        }
        Set-Location ..
        $maxDepth--
    }
    Write-Host " |> Found repository root at: $($PWD.Path)"

    if ($maxDepth -lt 0) {
        Write-Host " |> ERROR: Could not find repository directory."
        Write-Host " |> ERROR: Make sure to run this from within the repository."
        Write-Host " |> Exiting..."
        exit 1
    }
}

function Open-Venv {
    # Open venv (or set everything up if it doesn't exist)
    try {
        . .\venv\Scripts\Activate.ps1
    }
    catch {
        Write-Host " |> venv not set up. Creating one & installing dependencies"
        if (Get-Command python -ErrorAction SilentlyContinue) {
            python -m venv venv
        }
        else {
            Write-Host " |> ERROR: No python executable found."
            Write-Host " |> ERROR: Please install python to continue setup."
            Write-Host " |> Exiting..."
            exit 1
        }
        . .\venv\Scripts\Activate.ps1
        pip install -r "requirements.txt"
        Write-Host " |> `n |> `n |> "
    }
}
