$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$isccCandidates = @(
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles(x86)\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
)
$iscc = $isccCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $iscc) { throw "No se encontró Inno Setup 6. Instálalo con: winget install JRSoftware.InnoSetup" }

& "$projectRoot\build_windows.ps1"
& $iscc "$projectRoot\installer\YouTubeDownloader.iss"
Write-Host "Instalador creado en: $projectRoot\dist-installer"

