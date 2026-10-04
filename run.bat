@echo off
title PCSX2 Web Station & Bridge
echo Iniciando PCSX2 Web Station...
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERRO] Python nao foi encontrado no PATH. Por favor instale o Python em https://python.org
    pause
    exit /b
)
if not exist venv (
    echo Criando ambiente virtual...
    python -m venv venv
)
call venv\Scriptsctivate.bat
echo Instalando dependencias necessarias...
pip install -q -r requirements.txt
cls
echo ========================================================
echo   PCSX2 Web Station & Bridge rodando com sucesso!
echo   Acesse no navegador: http://127.0.0.1:8765
echo   Token padrao: pcsx2-token
echo ========================================================
python pcsx2_web.py
pause
