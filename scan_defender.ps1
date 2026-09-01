$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$target = "$projectRoot\dist\YouTube Video Downloader"
if (-not (Test-Path -LiteralPath $target)) { throw "Primero genera la aplicación con .\build_windows.ps1" }

$platform = Get-ChildItem -LiteralPath "$env:ProgramData\Microsoft\Windows Defender\Platform" -Directory -ErrorAction SilentlyContinue |
    Sort-Object Name -Descending | Select-Object -First 1
$mpCmdRun = if ($platform) { Join-Path $platform.FullName "MpCmdRun.exe" } else { "$env:ProgramFiles\Windows Defender\MpCmdRun.exe" }
if (-not (Test-Path -LiteralPath $mpCmdRun)) { throw "No se encontró la herramienta de línea de comandos de Microsoft Defender." }

& $mpCmdRun -Scan -ScanType 3 -File $target
$result = $LASTEXITCODE
if ($result -eq 0) { Write-Host "Microsoft Defender no detectó amenazas en la carpeta compilada."; exit 0 }
throw "Microsoft Defender devolvió el código $result. Revisa Historial de protección y MpCmdRun.log antes de distribuir."
