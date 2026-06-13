@echo off
REM ============================================================================
REM  Stigmergy — one-click launcher for Windows
REM  Double-click this file. It checks Docker, builds/starts the Stigmergy
REM  Compose stack, optionally downloads the LLM, and opens the dashboard.
REM ============================================================================
setlocal enabledelayedexpansion
title Stigmergy launcher

echo.
echo  ============================================
echo    Stigmergy - autonomous DFIR SOC (local)
echo  ============================================
echo.

REM --- locate the repo's deploy/ folder relative to this script ---------------
set "ROOT=%~dp0.."
set "REPO_URL=https://github.com/Shaugato/find-evil.git"

REM --- check Docker -----------------------------------------------------------
where docker >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Docker is not installed.
  echo         Install Docker Desktop: https://www.docker.com/products/docker-desktop/
  echo         Then re-run this launcher.
  pause & exit /b 1
)

REM --- locate the deploy\ stack: sibling repo, else clone --------------------
if exist "%ROOT%\deploy\docker-compose.yml" (
  pushd "%ROOT%\deploy"
  echo [ok] Using existing repo at %ROOT%
) else (
  where git >nul 2>&1
  if errorlevel 1 (
    echo [ERROR] git is not installed. Install Git for Windows, then re-run.
    echo         https://git-scm.com/download/win
    pause & exit /b 1
  )
  set "TARGET=%USERPROFILE%\find-evil"
  if exist "!TARGET!\deploy\docker-compose.yml" (
    echo [..] Updating existing checkout at !TARGET!
    git -C "!TARGET!" pull --ff-only
  ) else (
    echo [..] Cloning Stigmergy into !TARGET! ...
    git clone --depth 1 "%REPO_URL%" "!TARGET!"
    if errorlevel 1 ( echo [ERROR] git clone failed. & pause & exit /b 1 )
  )
  pushd "!TARGET!\deploy"
)

docker info >nul 2>&1
if errorlevel 1 (
  echo [..] Docker is installed but not running. Trying to start Docker Desktop...
  start "" "%ProgramFiles%\Docker\Docker\Docker Desktop.exe" 2>nul
  echo [..] Waiting up to 90s for the Docker engine...
  set /a tries=0
  :waitdocker
  timeout /t 5 >nul
  docker info >nul 2>&1 && goto dockerready
  set /a tries+=1
  if !tries! lss 18 goto waitdocker
  echo [ERROR] Docker engine did not start. Start Docker Desktop manually and retry.
  pause & exit /b 1
)
:dockerready
echo [ok] Docker engine is running.

if not exist .env copy .env.example .env >nul

REM --- optional LLM ----------------------------------------------------------
echo.
set /p LLM="Enable the AI narrator/pivot agents? Downloads ~2 GB model on first run [y/N]: "
if /i "!LLM!"=="y" ( set "ENABLE_LLM=1" ) else ( set "ENABLE_LLM=0" )

echo.
echo [..] Building and starting the Stigmergy stack (first run may take a few minutes)...
set ENABLE_LLM=!ENABLE_LLM!
docker compose up -d --build
if errorlevel 1 (
  echo [ERROR] docker compose failed. See the output above.
  pause & exit /b 1
)

echo [..] Waiting for the dashboard to come up...
set /a tries=0
:waitdash
timeout /t 3 >nul
curl -s -o nul http://localhost:9400/ 2>nul && goto dashready
set /a tries+=1
if !tries! lss 20 goto waitdash
:dashready

echo.
echo  ============================================
echo    Stigmergy is up.
echo      Dashboard : http://localhost:9400
echo      MCP       : http://localhost:9310/mcp
echo  ============================================
echo.
echo  Verify the forensic ledger:
echo      docker compose exec findevil findevil verify
echo.
start "" http://localhost:9400
echo  Press any key to view live logs (Ctrl+C to stop watching; stack keeps running).
pause >nul
docker compose logs -f findevil
popd
endlocal
