$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Executable = Join-Path $ProjectRoot "dist\CAPTEX\CAPTEX.exe"
if (-not (Test-Path -LiteralPath $Executable)) { throw "Packaged executable is missing: $Executable" }
$SmokeData = Join-Path $ProjectRoot "build\package-smoke-data"
if (Test-Path -LiteralPath $SmokeData) { Remove-Item -LiteralPath $SmokeData -Recurse -Force }
$env:CAPTEX_DATA_DIR = $SmokeData
$env:CAPTEX_NO_BROWSER = "true"
$env:CAPTEX_NO_DIALOG = "true"
$env:PORT = "8137"
$Process = Start-Process -FilePath $Executable -PassThru -WindowStyle Hidden
try {
    $Healthy = $false
    for ($Attempt = 0; $Attempt -lt 60; $Attempt++) {
        Start-Sleep -Milliseconds 500
        try {
            $Health = Invoke-RestMethod -Uri "http://127.0.0.1:8137/health" -TimeoutSec 1
            if ($Health.status -eq "healthy") { $Healthy = $true; break }
        } catch {}
        if ($Process.HasExited) { break }
    }
    if (-not $Healthy) { throw "Packaged CAPTEX did not become healthy. See $SmokeData\logs\captex.log" }
    $Setup = Invoke-WebRequest -Uri "http://127.0.0.1:8137/setup" -UseBasicParsing
    if ($Setup.StatusCode -ne 200 -or $Setup.Content -notmatch "Set up CAPTEX") { throw "Packaged setup page failed." }
    if (-not (Test-Path -LiteralPath (Join-Path $SmokeData "captex.db"))) { throw "Packaged database was not created." }
    $Environments = Invoke-RestMethod -Uri "http://127.0.0.1:8137/api/environments"
    if (-not ($Environments | Where-Object { $_.vagrant_path -eq "environments/ubuntu24" })) { throw "Managed VM environment was not registered." }
    Invoke-RestMethod -Uri "http://127.0.0.1:8137/api/application/exit" -Method Post | Out-Null
    $Process.WaitForExit(10000) | Out-Null
    if (-not $Process.HasExited) { throw "Exit CAPTEX did not stop the packaged process." }
    Write-Host "Packaged application smoke test passed."
} finally {
    if (-not $Process.HasExited) { Stop-Process -Id $Process.Id -Force }
    Remove-Item Env:CAPTEX_DATA_DIR -ErrorAction SilentlyContinue
    Remove-Item Env:CAPTEX_NO_BROWSER -ErrorAction SilentlyContinue
    Remove-Item Env:CAPTEX_NO_DIALOG -ErrorAction SilentlyContinue
    Remove-Item Env:PORT -ErrorAction SilentlyContinue
}
