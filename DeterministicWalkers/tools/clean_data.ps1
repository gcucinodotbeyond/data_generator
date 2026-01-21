# clean_data.ps1
# This script removes the 'data' folder and its contents.
# The folder is recreated automatically when running main.py.

$dataPath = Join-Path $PSScriptRoot "..\data"

if (Test-Path $dataPath) {
    Write-Host "[System] Removing 'data' folder at: $dataPath" -ForegroundColor Cyan
    Remove-Item -Path $dataPath -Recurse -Force
    Write-Host "[System] Cleanup complete." -ForegroundColor Green
} else {
    Write-Host "[System] 'data' folder not found. Nothing to clean." -ForegroundColor Yellow
}
