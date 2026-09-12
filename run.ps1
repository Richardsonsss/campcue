# Starts MongoDB, the Django backend, and the React frontend, each in its
# own window. Close a window (or Ctrl+C in it) to stop that service.
#
# First-time setup still applies: backend venv/requirements installed,
# frontend `npm install` run, and MongoDB seeded (see README.md).
#
# Usage:  powershell -ExecutionPolicy Bypass -File run.ps1

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

# `python`/`python3` on PATH can resolve to the Microsoft Store's App
# Execution Alias, which hangs instead of running anything - prefer a real
# installed interpreter when one is found.
$candidates = @("C:\Python314\python.exe", "python")
$python = $candidates | Where-Object { Test-Path $_ -PathType Leaf -ErrorAction SilentlyContinue } | Select-Object -First 1
if (-not $python) { $python = "python" }

$mongodExe = Join-Path $root ".mongodb\bin\mongod.exe"
$mongoData = Join-Path $root ".mongodb\data"

if (-not (Test-Path $mongoData)) {
    New-Item -ItemType Directory -Force -Path $mongoData | Out-Null
}

function Test-PortOpen($port) {
    $conn = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    return $null -ne $conn
}

Write-Host "Starting MongoDB..." -ForegroundColor Cyan
if (Test-PortOpen 27017) {
    Write-Host "  Already running on port 27017." -ForegroundColor DarkGray
} elseif (Test-Path $mongodExe) {
    Start-Process powershell -ArgumentList @(
        "-NoExit", "-Command",
        "& '$mongodExe' --dbpath '$mongoData' --port 27017 --bind_ip 127.0.0.1"
    )
} else {
    Write-Host "  No local MongoDB found at $mongodExe - start your own instance, or run 'docker compose up mongo'." -ForegroundColor Yellow
}

Write-Host "Starting Django backend on :8000..." -ForegroundColor Cyan
if (Test-PortOpen 8000) {
    Write-Host "  Already running on port 8000." -ForegroundColor DarkGray
} else {
    $backendDir = Join-Path $root "backend"
    Start-Process powershell -ArgumentList @(
        "-NoExit", "-Command",
        "cd '$backendDir'; & $python manage.py runserver 8000"
    )
}

Write-Host "Starting React frontend on :5173..." -ForegroundColor Cyan
if (Test-PortOpen 5173) {
    Write-Host "  Already running on port 5173." -ForegroundColor DarkGray
} else {
    $frontendDir = Join-Path $root "frontend"
    Start-Process powershell -ArgumentList @(
        "-NoExit", "-Command",
        "cd '$frontendDir'; npm run dev"
    )
}

Write-Host ""
Write-Host "Once all three windows say they're ready:" -ForegroundColor Green
Write-Host "  App:     http://localhost:5173"
Write-Host "  API:     http://localhost:8000/api/campgrounds/"
