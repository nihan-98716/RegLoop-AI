# deploy-prod.ps1 — Production deployment script for RegLoop AI (Windows PowerShell)
#
# Usage:
#   .\deploy-prod.ps1
#
# Prerequisites:
#   - Docker Desktop installed and running
#   - .env file populated (copy from .env.example and fill in secrets)
#
# What this script does:
#   1. Validates required environment variables are set
#   2. Builds and starts all Docker services using PostgreSQL
#   3. Waits for the backend to become healthy before exiting

param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "==> RegLoop AI — Production Deployment (Windows)" -ForegroundColor Cyan

# ── 1. Load .env file if present ──────────────────────────────────────────────
$envFile = Join-Path $PSScriptRoot ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match "^\s*([^#][^=]+)=(.*)$") {
            $key = $Matches[1].Trim()
            $value = $Matches[2].Trim()
            [System.Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
    Write-Host "  Loaded environment from .env" -ForegroundColor Green
}

# ── 2. Environment validation ─────────────────────────────────────────────────
$requiredVars = @("DATABASE_URL", "OPENAI_API_KEY")
foreach ($var in $requiredVars) {
    $val = [System.Environment]::GetEnvironmentVariable($var, "Process")
    if ([string]::IsNullOrWhiteSpace($val)) {
        Write-Error "Required environment variable '$var' is not set. Copy .env.example to .env and fill in all values."
        exit 1
    }
}

# Export production database URL (PostgreSQL)
$env:PROD_DATABASE_URL = $env:DATABASE_URL

$dbDisplay = ($env:DATABASE_URL -replace "//[^@]+@", "//*:*@")
Write-Host "  Database : $dbDisplay" -ForegroundColor Gray
Write-Host "  LLM      : $($env:LLM_PROVIDER ?? 'openai')" -ForegroundColor Gray

# ── 3. Build and start services ───────────────────────────────────────────────
Write-Host "==> Building Docker images..." -ForegroundColor Cyan
docker compose build --no-cache
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> Starting services..." -ForegroundColor Cyan
docker compose up -d
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# ── 4. Health check ───────────────────────────────────────────────────────────
Write-Host "==> Waiting for backend to become healthy..." -ForegroundColor Cyan
$retries = 30
$healthy = $false
while ($retries -gt 0) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($response.StatusCode -eq 200) { $healthy = $true; break }
    } catch { }
    $retries--
    Start-Sleep -Seconds 2
}

if (-not $healthy) {
    Write-Error "Backend health check timed out. Run 'docker compose logs backend' to diagnose."
    exit 1
}

Write-Host ""
Write-Host "✅ RegLoop AI is running!" -ForegroundColor Green
Write-Host "   Frontend  : http://localhost:3000"
Write-Host "   API       : http://localhost:8000"
Write-Host "   API Docs  : http://localhost:8000/docs"
