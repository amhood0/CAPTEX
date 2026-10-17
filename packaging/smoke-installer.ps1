$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Installer = Join-Path $ProjectRoot "dist\installer\CAPTEX-Setup-0.1.0.exe"
$InstallDir = Join-Path $ProjectRoot "build\installer-smoke\app"
$DataDir = Join-Path $ProjectRoot "build\installer-smoke\data"
$SafeRoot = Join-Path $ProjectRoot "build\installer-smoke"
if (-not $InstallDir.StartsWith($SafeRoot) -or -not $DataDir.StartsWith($SafeRoot)) { throw "Unsafe smoke paths." }
if (Test-Path -LiteralPath $SafeRoot) { Remove-Item -LiteralPath $SafeRoot -Recurse -Force }
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

$InstallLog = Join-Path $SafeRoot "install.log"
$InstallProcess = Start-Process -FilePath $Installer -ArgumentList "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/SP-", "/DIR=`"$InstallDir`"", "/LOG=`"$InstallLog`"" -Wait -PassThru -WindowStyle Hidden
if ($InstallProcess.ExitCode -ne 0) { throw "Silent installer failed with exit code $($InstallProcess.ExitCode)." }
$Executable = Join-Path $InstallDir "CAPTEX.exe"
if (-not (Test-Path -LiteralPath $Executable)) { throw "Installer did not deploy CAPTEX.exe." }

$env:CAPTEX_DATA_DIR = $DataDir
$env:CAPTEX_NO_BROWSER = "true"
$env:CAPTEX_NO_DIALOG = "true"
$env:PORT = "8138"
$Process = Start-Process -FilePath $Executable -PassThru -WindowStyle Hidden
try {
    $Healthy = $false
    for ($Attempt = 0; $Attempt -lt 60; $Attempt++) {
        Start-Sleep -Milliseconds 500
        try {
            $Health = Invoke-RestMethod -Uri "http://127.0.0.1:8138/health" -TimeoutSec 1
            if ($Health.status -eq "healthy") { $Healthy = $true; break }
        } catch {}
        if ($Process.HasExited) { break }
    }
    if (-not $Healthy) { throw "Installed CAPTEX did not become healthy." }
    if (-not (Test-Path -LiteralPath (Join-Path $DataDir "captex.db"))) { throw "Installed CAPTEX did not initialize its database." }
    $Environments = Invoke-RestMethod -Uri "http://127.0.0.1:8138/api/environments"
    if (-not ($Environments | Where-Object { $_.vagrant_path -eq "environments/ubuntu24" })) { throw "Installed CAPTEX did not register its managed VM." }
    Invoke-RestMethod -Uri "http://127.0.0.1:8138/api/application/exit" -Method Post | Out-Null
    $Process.WaitForExit(10000) | Out-Null
    if (-not $Process.HasExited) { throw "Exit CAPTEX did not stop the installed process." }
    Write-Host "Installer smoke test passed."
} finally {
    if (-not $Process.HasExited) { Stop-Process -Id $Process.Id -Force }
    Remove-Item Env:CAPTEX_DATA_DIR -ErrorAction SilentlyContinue
    Remove-Item Env:CAPTEX_NO_BROWSER -ErrorAction SilentlyContinue
    Remove-Item Env:CAPTEX_NO_DIALOG -ErrorAction SilentlyContinue
    Remove-Item Env:PORT -ErrorAction SilentlyContinue
}

$Uninstaller = Join-Path $InstallDir "unins000.exe"
if (Test-Path -LiteralPath $Uninstaller) {
    $UninstallProcess = Start-Process -FilePath $Uninstaller -ArgumentList "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART" -Wait -PassThru -WindowStyle Hidden
    if ($UninstallProcess.ExitCode -ne 0) { throw "Smoke-test uninstall failed." }
}
