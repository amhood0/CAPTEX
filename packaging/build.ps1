$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$PackageRoot = Join-Path $env:TEMP "captex-build-$PID"
if (-not (Test-Path -LiteralPath $Python)) { throw "Create .venv and install requirements-build.txt first." }

Push-Location $ProjectRoot
try {
    & $Python -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw "Tests failed; packaging stopped." }
    if (Test-Path -LiteralPath $PackageRoot) { Remove-Item -LiteralPath $PackageRoot -Recurse -Force }
    & $Python -m PyInstaller --noconfirm --distpath (Join-Path $PackageRoot "dist") --workpath (Join-Path $PackageRoot "build") CAPTEX.spec
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed." }
    $Portable = Join-Path $ProjectRoot "dist\CAPTEX"
    New-Item -ItemType Directory -Force -Path $Portable | Out-Null
    Copy-Item -Path (Join-Path $PackageRoot "dist\CAPTEX\*") -Destination $Portable -Recurse -Force

    & (Join-Path $PSScriptRoot "smoke-package.ps1")

    $CompilerCandidates = @(
        (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe")
    )
    $Compiler = $CompilerCandidates | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -First 1
    if ($Compiler) {
        & $Compiler (Join-Path $PSScriptRoot "CAPTEX.iss")
        if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed." }
        & (Join-Path $PSScriptRoot "smoke-installer.ps1")
        Write-Host "Installer: $ProjectRoot\dist\installer\CAPTEX-Setup-0.1.0.exe"
    } else {
        Write-Warning "Inno Setup 6 is not installed. The tested portable build is in dist\CAPTEX."
    }
} finally {
    Pop-Location
    if (Test-Path -LiteralPath $PackageRoot) { Remove-Item -LiteralPath $PackageRoot -Recurse -Force }
}
