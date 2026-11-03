# Pre-push gate: full test suite + import smoke + schema drift + security scan
# Runs before every push. Must pass before code reaches the box.

$ErrorActionPreference = "Stop"

$base = "C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform"
$env:PYTHONPATH = "$base\packages;$base\apps"

Write-Host "=== Pre-push gate ===" -ForegroundColor Cyan

# 1. Full test suite (including e2e if markers exist)
Write-Host "[1/5] pytest full suite..." -ForegroundColor Yellow
python -m pytest tests/ -q --tb=short
if ($LASTEXITCODE -ne 0) { Write-Host "FAIL: pytest full suite" -ForegroundColor Red; exit 1 }

# 2. Import smoke
Write-Host "[2/5] import smoke..." -ForegroundColor Yellow
python scripts/import_smoke.py
if ($LASTEXITCODE -ne 0) { Write-Host "FAIL: import smoke" -ForegroundColor Red; exit 1 }

# 3. Schema drift gate
Write-Host "[3/5] schema drift..." -ForegroundColor Yellow
python scripts/schema_drift_gate.py
if ($LASTEXITCODE -ne 0) { Write-Host "FAIL: schema drift" -ForegroundColor Red; exit 1 }

# 4. Security scan
Write-Host "[4/5] security scan..." -ForegroundColor Yellow
python scripts/security_scan.py
if ($LASTEXITCODE -ne 0) { Write-Host "FAIL: security scan" -ForegroundColor Red; exit 1 }

# 5. Consumer wiring audit (shared import + kwarg truth)
if (Test-Path "$base\scripts\consumer_wiring_audit.py") {
    Write-Host "[5/5] consumer wiring audit..." -ForegroundColor Yellow
    python scripts/consumer_wiring_audit.py
    if ($LASTEXITCODE -ne 0) { Write-Host "FAIL: consumer wiring audit" -ForegroundColor Red; exit 1 }
} else {
    Write-Host "[5/5] consumer wiring audit not found, skipping" -ForegroundColor Yellow
}

Write-Host "=== Pre-push gate PASSED ===" -ForegroundColor Green
