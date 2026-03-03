# Development startup script for Chrome Extension History Backend
# Run this script to start the backend services for development

Write-Host "🚀 Starting Chrome Extension History Backend..." -ForegroundColor Green

# Check if Docker is running
try {
    docker version | Out-Null
    Write-Host "✅ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker is not running. Please start Docker Desktop first." -ForegroundColor Red
    exit 1
}

# Navigate to project root
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptPath
Set-Location $projectRoot

Write-Host "📂 Project root: $projectRoot" -ForegroundColor Yellow

# Build and start services
Write-Host "🔨 Building and starting services..." -ForegroundColor Yellow
docker compose up --build -d

# Wait for services to be healthy
Write-Host "⏳ Waiting for services to be ready..." -ForegroundColor Yellow
$timeout = 60
$elapsed = 0
$interval = 5

do {
    Start-Sleep $interval
    $elapsed += $interval
    
    # If migrations exited, fail only when exit code is non-zero.
    $migrateContainerId = docker compose ps -a -q migrate 2>$null
    if ($migrateContainerId) {
        $migrateExitCode = docker inspect --format '{{.State.ExitCode}}' $migrateContainerId 2>$null
        if ($migrateExitCode -and [int]$migrateExitCode -ne 0) {
            Write-Host "❌ Migration service failed. Displaying logs..." -ForegroundColor Red
            docker compose logs migrate
            exit 1
        }
    }

    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get -TimeoutSec 5
        if ($response.status -eq "healthy") {
            Write-Host "✅ Backend is ready!" -ForegroundColor Green
            break
        }
    } catch {
        Write-Host "⏳ Still waiting for backend... ($elapsed/$timeout seconds)" -ForegroundColor Yellow
    }
    
    if ($elapsed -ge $timeout) {
        Write-Host "❌ Timeout waiting for services to be ready" -ForegroundColor Red
        Write-Host "Run 'docker compose logs backend migrate' to check for errors" -ForegroundColor Yellow
        exit 1
    }
} while ($true)

# Show service status
Write-Host "`n📊 Service Status:" -ForegroundColor Cyan
docker compose ps

Write-Host "`n🎉 Development environment is ready!" -ForegroundColor Green
Write-Host "🌐 Backend API: http://localhost:8000" -ForegroundColor Cyan
Write-Host "📚 API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "🔧 To stop services: .\scripts\dev_down.ps1" -ForegroundColor Yellow
Write-Host "📋 To view logs: docker compose logs -f backend" -ForegroundColor Yellow
