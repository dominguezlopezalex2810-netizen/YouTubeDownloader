$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $projectRoot

if (-not (Test-Path -LiteralPath "$projectRoot\bin\ffmpeg.exe")) {
    throw "Falta bin\ffmpeg.exe. Ejecuta primero .\prepare_ffmpeg.ps1"
}
python -m pip install -r requirements-dev.txt
python -m pytest
python -m PyInstaller --noconfirm --clean YouTubeDownloader.spec

Write-Host "Aplicación creada en: $projectRoot\dist\YouTube Video Downloader"
Write-Host "Ejecutable: $projectRoot\dist\YouTube Video Downloader\YouTube Video Downloader.exe"
Write-Host "Ejecuta .\scan_defender.ps1 para analizar el resultado con Microsoft Defender."
