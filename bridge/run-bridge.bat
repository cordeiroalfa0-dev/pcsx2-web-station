@echo off
setlocal
cd /d "%~dp0"
where node >nul 2>nul
if errorlevel 1 (
  echo Node.js 18 ou superior nao foi encontrado.
  echo Instale em https://nodejs.org/ e execute este arquivo novamente.
  pause
  exit /b 1
)
node bridge.mjs
pause
