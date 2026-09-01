$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$binDir = Join-Path $projectRoot "bin"
$workDir = Join-Path $projectRoot "work-ffmpeg"
$archive = Join-Path $workDir "ffmpeg-win64-lgpl.zip"

# Asset BtbN LGPL win64 del 31-08-2026. La descarga solo ocurre al preparar una build,
# nunca al ejecutar la aplicación instalada.
$assetUrl = "https://api.github.com/repos/BtbN/FFmpeg-Builds/releases/assets/538054271"
$expectedSha256 = "00E72BA1E21E6B4B7E77620DF85B3C8F2712D3550206CA9ECFFA2E0470E637FB"

New-Item -ItemType Directory -Force -Path $binDir, $workDir | Out-Null
Invoke-WebRequest -Headers @{ "Accept"="application/octet-stream"; "User-Agent"="YouTubeDownloader-build" } -Uri $assetUrl -OutFile $archive
$actualSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $archive).Hash
if ($actualSha256 -ne $expectedSha256) { throw "El hash SHA-256 del paquete FFmpeg no coincide. Se cancela la preparación." }

Expand-Archive -LiteralPath $archive -DestinationPath $workDir -Force
$ffmpeg = Get-ChildItem -LiteralPath $workDir -Recurse -Filter "ffmpeg.exe" | Select-Object -First 1
$ffprobe = Get-ChildItem -LiteralPath $workDir -Recurse -Filter "ffprobe.exe" | Select-Object -First 1
if (-not $ffmpeg -or -not $ffprobe) { throw "El paquete verificado no contiene ffmpeg.exe y ffprobe.exe." }
Copy-Item -LiteralPath $ffmpeg.FullName -Destination "$binDir\ffmpeg.exe" -Force
Copy-Item -LiteralPath $ffprobe.FullName -Destination "$binDir\ffprobe.exe" -Force
Copy-Item -LiteralPath (Join-Path $ffmpeg.Directory.Parent.FullName "LICENSE.txt") -Destination "$binDir\FFMPEG-LICENSE.txt" -Force -ErrorAction SilentlyContinue

Write-Host "FFmpeg preparado en $binDir"
