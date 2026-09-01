param(
    [Parameter(Mandatory=$true)][string]$CertificateThumbprint,
    [string]$TimestampUrl = "http://timestamp.digicert.com"
)
$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$signtool = Get-Command signtool.exe -ErrorAction SilentlyContinue
if (-not $signtool) { throw "No se encontró signtool.exe. Instala Windows SDK y añade su carpeta bin al PATH." }

$targets = @()
$appExe = "$projectRoot\dist\YouTube Video Downloader\YouTube Video Downloader.exe"
if (Test-Path -LiteralPath $appExe) { $targets += $appExe }
$targets += Get-ChildItem -LiteralPath "$projectRoot\dist-installer" -Filter "*.exe" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName
if ($targets.Count -eq 0) { throw "No hay binarios compilados para firmar." }

foreach ($target in $targets) {
    & $signtool.Source sign /sha1 $CertificateThumbprint /fd SHA256 /tr $TimestampUrl /td SHA256 $target
    if ($LASTEXITCODE -ne 0) { throw "Falló la firma de $target" }
    & $signtool.Source verify /pa /v $target
    if ($LASTEXITCODE -ne 0) { throw "Falló la verificación de $target" }
}

