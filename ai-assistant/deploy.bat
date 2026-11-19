@echo off
REM ===========================================================================
REM Deploy AI Assistant to the Hostinger VPS (Windows).
REM
REM One deployment serves every agent product via capability-based access.
REM
REM   1. Build the private shared-canonical-services wheel (sibling repo)
REM   2. Stage it in .\dist\ so the Docker build can install it
REM   3. Package + upload to the VPS
REM   4. Start PostgreSQL/Redis, init schema, build + start the app, start Nginx
REM ===========================================================================

setlocal enabledelayedexpansion

set VPS_HOST=201.18.210.61
set VPS_USER=root
set DEPLOY_PATH=/opt/ai-assistant
set COMPOSE_FILE=docker-compose.yml
set ENV_FILE=.env

set PROJECT_ROOT=%~dp0
if "%PROJECT_ROOT:~-1%"=="\" set PROJECT_ROOT=%PROJECT_ROOT:~0,-1%
set CANONICAL_REPO=%PROJECT_ROOT%\..\shared-canonical-services
set WHEEL_DIR=%PROJECT_ROOT%\dist
set PACKAGE=%PROJECT_ROOT%\deploy\ai-assistant.tar.gz

set DB_USER=ai_assistant
set DB_NAME=ai_assistant

echo =================================================
echo  Deploying AI Assistant to %VPS_HOST%
echo =================================================

REM --- Pre-flight -----------------------------------------------------------
if not exist "%PROJECT_ROOT%\%COMPOSE_FILE%" (
    echo [FAIL] %COMPOSE_FILE% not found
    exit /b 1
)
if not exist "%PROJECT_ROOT%\Dockerfile" (
    echo [FAIL] Dockerfile not found
    exit /b 1
)
if not exist "%PROJECT_ROOT%\nginx.conf" (
    echo [FAIL] nginx.conf not found
    exit /b 1
)
if not exist "%PROJECT_ROOT%\init-db.sh" (
    echo [FAIL] init-db.sh not found
    exit /b 1
)

if not exist "%PROJECT_ROOT%\%ENV_FILE%" (
    echo [WARN] %ENV_FILE% not found, creating from .env.example
    copy "%PROJECT_ROOT%\.env.example" "%PROJECT_ROOT%\%ENV_FILE%" >nul
    echo [FAIL] Please edit %ENV_FILE% with your credentials, then re-run
    exit /b 1
)

REM --- Validate required env vars -------------------------------------------
for /f "tokens=1,* delims==" %%a in ('findstr /b "SECRET_KEY= POSTGRES_PASSWORD= PII_ENCRYPTION_KEY= CREDENTIAL_ENCRYPTION_KEY=" "%PROJECT_ROOT%\%ENV_FILE%"') do (
    if "%%b"=="" (
        echo [FAIL] Required variable %%a is not set in %ENV_FILE%
        exit /b 1
    )
)
echo [OK] Environment validated

REM --- Build the private shared wheel ----------------------------------------
echo [INFO] Building shared-canonical-services wheel from %CANONICAL_REPO%
pushd "%CANONICAL_REPO%"
python -m pip install --upgrade pip build >nul
python -m build --wheel
popd

if not exist "%CANONICAL_REPO%\dist" (
    echo [FAIL] No dist folder in %CANONICAL_REPO%
    exit /b 1
)

REM Newest wheel wins
set WHEEL=
for /f "delims=" %%w in ('dir /b /o-d "%CANONICAL_REPO%\dist\shared_canonical_services-*.whl" 2^>nul') do (
    if not defined WHEEL set WHEEL=%%w
)
if not defined WHEEL (
    echo [FAIL] No wheel produced in %CANONICAL_REPO%\dist
    exit /b 1
)

REM Guard against the nested-repo pitfall (empty wheel)
for %%A in ("%CANONICAL_REPO%\dist\%WHEEL%") do set WHEEL_SIZE=%%~zA
if !WHEEL_SIZE! LSS 100000 (
    echo [FAIL] Wheel is only !WHEEL_SIZE! bytes - nested build pitfall?
    exit /b 1
)
echo [OK] Built %WHEEL%

if not exist "%WHEEL_DIR%" mkdir "%WHEEL_DIR%"
del /q "%WHEEL_DIR%\*.whl" 2>nul
copy "%CANONICAL_REPO%\dist\%WHEEL%" "%WHEEL_DIR%\" >nul

REM --- Package ---------------------------------------------------------------
echo [INFO] Creating deployment package
if not exist "%PROJECT_ROOT%\deploy" mkdir "%PROJECT_ROOT%\deploy"
if exist "%PACKAGE%" del "%PACKAGE%"

pushd "%PROJECT_ROOT%"
tar -czf "%PACKAGE%" ^
    --exclude=.git ^
    --exclude=__pycache__ ^
    --exclude=*.pyc ^
    --exclude=node_modules ^
    --exclude=.venv ^
    --exclude=venv ^
    --exclude=app/static ^
    "%COMPOSE_FILE%" ^
    Dockerfile ^
    nginx.conf ^
    init-db.sh ^
    dist ^
    "%ENV_FILE%"
popd

echo [OK] Package: %PACKAGE%

REM --- Upload ----------------------------------------------------------------
echo [INFO] Uploading to %VPS_USER%@%VPS_HOST%
ssh %VPS_USER%@%VPS_HOST% "mkdir -p %DEPLOY_PATH%"
scp "%PACKAGE%" "%VPS_USER%@%VPS_HOST%:/root/ai-assistant.tar.gz"
if errorlevel 1 (
    echo [FAIL] Upload failed
    exit /b 1
)

REM --- Deploy ----------------------------------------------------------------
echo [INFO] Deploying...
ssh %VPS_USER%@%VPS_HOST% ^
  "set -e; cd %DEPLOY_PATH%; echo 'Extracting package...'; tar -xzf /root/ai-assistant.tar.gz; cp .env .env; echo 'Starting PostgreSQL and Redis...'; docker compose -f %COMPOSE_FILE% up -d postgres redis; echo 'Waiting for PostgreSQL...'; for i in \$(seq 1 30); do docker compose -f %COMPOSE_FILE% exec -T postgres pg_isready -U %DB_USER% -d %DB_NAME% >/dev/null 2^\^&2 && break; sleep 2; done; echo 'Waiting for Redis...'; for i in \$(seq 1 15); do docker compose -f %COMPOSE_FILE% exec -T redis redis-cli ping >/dev/null 2^\^&2 && break; sleep 2; done; echo 'Building ai-assistant image...'; docker compose -f %COMPOSE_FILE% build ai-assistant; echo 'Starting ai-assistant...'; docker compose -f %COMPOSE_FILE% up -d ai-assistant; echo 'Waiting for health...'; for i in \$(seq 1 40); do curl -sf http://localhost:8000/health >/dev/null 2^\^&1 && break; sleep 3; done; echo 'Starting Nginx...'; docker compose -f %COMPOSE_FILE% up -d nginx; echo 'Requesting TLS certificates...'; docker compose -f %COMPOSE_FILE% run --rm --entrypoint '' certbot certonly --webroot -w /var/www/certbot -d ai.snapford.com -d app.ai.snapford.com -d api.ai.snapford.com --email admin@snapford.com --agree-tos --no-eff-email || echo 'Certbot will retry'; docker compose -f %COMPOSE_FILE% restart nginx; echo ''; echo 'Deployment complete.'; echo '  Landing:  https://ai.snapford.com'; echo '  Dashboard: https://app.ai.snapford.com'; echo '  API:      https://api.ai.snapford.com'; echo '  Health:   https://ai.snapford.com/health'"

echo.
echo [OK] AI Assistant deployed to %VPS_HOST%
echo    Landing:   https://ai.snapford.com
echo    Dashboard: https://app.ai.snapford.com
echo    API:       https://api.ai.snapford.com

pause
