param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

if (-not (Test-Path -LiteralPath (Join-Path $projectRoot "app.py"))) {
    throw "Run this script from a Personal OS repository checkout. app.py was not found."
}

if ($Python -eq "python" -and (Test-Path -LiteralPath (Join-Path $projectRoot ".venv\Scripts\python.exe"))) {
    $Python = Join-Path $projectRoot ".venv\Scripts\python.exe"
}

$env:PERSONAL_OS_ENV = "verification"
$env:PERSONAL_OS_PORT = "8877"
Remove-Item Env:PERSONAL_OS_DB_PATH -ErrorAction SilentlyContinue
Remove-Item Env:PERSONAL_OS_BACKUP_DIR -ErrorAction SilentlyContinue
Remove-Item Env:PERSONAL_OS_ATTACHMENT_DIR -ErrorAction SilentlyContinue

$verificationDatabase = Join-Path $projectRoot "data\verification\personal_os_verification.db"
if (-not (Test-Path -LiteralPath $verificationDatabase)) {
    throw "Verification database is missing. Run tools/create_verification_db.py first."
}

Write-Host "Personal OS verification: http://localhost:8877"
$lanAddress = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } |
    Select-Object -First 1 -ExpandProperty IPAddress
if ([string]::IsNullOrWhiteSpace($lanAddress)) { $lanAddress = '127.0.0.1' }
Write-Host "iPhone (same Wi-Fi): http://${lanAddress}:8877"
Push-Location $projectRoot
try {
    & $Python "app.py"
}
finally {
    Pop-Location
}
