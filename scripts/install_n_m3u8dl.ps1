param(
    [string]$InstallDir = "$PSScriptRoot\..\tools\N_m3u8DL-CLI"
)

$ErrorActionPreference = "Stop"
$releaseApi = "https://api.github.com/repos/nilaoda/N_m3u8DL-CLI/releases/latest"
$installPath = Resolve-Path "$PSScriptRoot\.."
$targetDir = [System.IO.Path]::GetFullPath((Join-Path $installPath "tools\N_m3u8DL-CLI"))
if ($InstallDir) {
    $targetDir = [System.IO.Path]::GetFullPath($InstallDir)
}

Write-Host "Fetching latest N_m3u8DL-CLI release metadata..."
$release = Invoke-RestMethod -Uri $releaseApi -Headers @{ "User-Agent" = "batch-video-downloader" }

$asset = $release.assets |
    Where-Object {
        $_.name -match "win|windows" -and
        $_.name -match "x64|win64|windows" -and
        $_.name -match "\.zip$"
    } |
    Select-Object -First 1

if (-not $asset) {
    $asset = $release.assets | Where-Object { $_.name -match "\.zip$" } | Select-Object -First 1
}

if (-not $asset) {
    throw "No zip asset was found in the latest release."
}

New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
$zipPath = Join-Path $env:TEMP $asset.name

Write-Host "Downloading $($asset.name)..."
Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $zipPath -Headers @{ "User-Agent" = "batch-video-downloader" }

Write-Host "Extracting to $targetDir..."
Expand-Archive -Path $zipPath -DestinationPath $targetDir -Force

$exe = Get-ChildItem -Path $targetDir -Recurse -Filter "N_m3u8DL-CLI.exe" | Select-Object -First 1
if (-not $exe) {
    throw "N_m3u8DL-CLI.exe was not found after extraction."
}

Write-Host "Installed: $($exe.FullName)"
