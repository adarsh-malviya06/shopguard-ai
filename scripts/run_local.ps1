# ShopGuard AI — Local Multi-Service Launcher
# Starts Simulator (8002), Backend (8010), and Streamlit (8501)

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "🛡️  STARTING SHOPGUARD AI MULTI-SERVICE ENVIRONMENT" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$venvPython = ".\.venv\Scripts\python.exe"
$venvStreamlit = ".\.venv\Scripts\streamlit.exe"

# 1. Start Simulator on Port 8002
Write-Host "[1/3] Starting E-Commerce Simulator on http://localhost:8002..." -ForegroundColor Green
Start-Process $venvPython -ArgumentList "-m", "uvicorn", "src.shopguard.simulator.main:app", "--port", "8002", "--host", "0.0.0.0"

# 2. Start ShopGuard Backend on Port 8010
Write-Host "[2/3] Starting ShopGuard Co-Pilot Backend on http://localhost:8010..." -ForegroundColor Green
Start-Process $venvPython -ArgumentList "-m", "uvicorn", "src.shopguard.api.main:app", "--port", "8010", "--host", "0.0.0.0"

# 3. Start Streamlit Dashboard on Port 8501
Write-Host "[3/3] Starting Streamlit Dashboard on http://localhost:8501..." -ForegroundColor Green
Start-Process $venvStreamlit -ArgumentList "run", "ui/app.py", "--server.port", "8501", "--server.headless", "true"

Write-Host "`nAll 3 services launched in background!" -ForegroundColor Yellow
Write-Host "Dashboard: http://localhost:8501" -ForegroundColor Cyan
Write-Host "Backend API: http://localhost:8010/docs" -ForegroundColor Cyan
Write-Host "Simulator API: http://localhost:8002/docs" -ForegroundColor Cyan

