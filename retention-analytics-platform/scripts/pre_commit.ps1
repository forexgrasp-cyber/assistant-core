# Pre-commit gate: lint + typecheck + fast tests on staged files
# Runs before every commit. Must pass before push.

$base = "C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform"
$env:PYTHONPATH = "$base\packages;$base\apps"

Write-Host "=== Pre-commit gate ===" -ForegroundColor Cyan

# 1. Lint
Write-Host "[1/3] ruff check..." -ForegroundColor Yellow
ruff check packages/ apps/ tests/
if ($LASTEXITCODE -ne 0) { Write-Host "FAIL: ruff check" -ForegroundColor Red; exit 1 }

# 2. Typecheck (mypy if available)
if (Get-Command mypy -ErrorAction SilentlyContinue) {
    Write-Host "[2/3] mypy..." -ForegroundColor Yellow
    mypy packages/retention_analytics_core packages/retention_analytics_engagement apps/api/
    if ($LASTEXITCODE -ne 0) { Write-Host "FAIL: mypy" -ForegroundColor Red; exit 1 }
} else {
    Write-Host "[2/3] mypy not installed, skipping" -ForegroundColor Yellow
}

# 3. Fast tests (exclude e2e)
Write-Host "[3/3] pytest (fast, no e2e)..." -ForegroundColor Yellow
python -m pytest tests/ -q -m "not e2e" --tb=short
if ($LASTEXITCODE -ne 0) { Write-Host "FAIL: pytest" -ForegroundColor Red; exit 1 }

Write-Host "=== Pre-commit gate PASSED ===" -ForegroundColor Green