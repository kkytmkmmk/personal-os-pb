param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$snapshotRoot = Join-Path $projectRoot "dist\public"
$pythonArguments = @()
if ($Python -eq "python") {
    $venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $venvPython) {
        $Python = $venvPython
    } elseif (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        $launcher = Get-Command py -ErrorAction SilentlyContinue
        if (-not $launcher) {
            throw "Python was not found. Install Python or create .venv before running the public-release check."
        }
        $Python = $launcher.Source
        $pythonArguments = @("-3")
    }
}

function Invoke-PythonCheck([string[]]$Arguments) {
    & $Python @pythonArguments @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Check failed: $($Arguments -join ' ')"
    }
}

Push-Location $projectRoot
try {
    Invoke-PythonCheck @("tools/check_secrets.py", "--root", ".")
    Invoke-PythonCheck @("tools/check_public_safety.py", "--root", ".")
    Invoke-PythonCheck @("tools/check_tracked_private_files.py", "--root", ".")
    Invoke-PythonCheck @("-m", "unittest", "discover", "-s", "tests", "-v")
    Invoke-PythonCheck @("tools/run_memory_quality_benchmark.py")
    Invoke-PythonCheck @("tools/build_public_snapshot.py", "--output", $snapshotRoot)
    Invoke-PythonCheck @("tools/check_secrets.py", "--root", $snapshotRoot)
    Invoke-PythonCheck @("tools/check_public_safety.py", "--root", $snapshotRoot)
    Write-Host "PUBLIC READY WITH MANUAL CHECK: automated checks passed. Snapshot: $snapshotRoot"
}
finally {
    Pop-Location
}
