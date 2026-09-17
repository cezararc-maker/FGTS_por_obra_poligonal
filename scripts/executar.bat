@echo off
setlocal
cd /d "%~dp0.."

if not exist ".venv\Scripts\python.exe" (
    echo [ERRO] Ambiente .venv nao encontrado.
    echo Execute primeiro: scripts\instalar_teste.bat
    pause
    exit /b 1
)

set "PYTHONPATH=%CD%\src"
".venv\Scripts\python.exe" -m fgts_obra.app_final

if errorlevel 1 (
    echo.
    echo [ERRO] A aplicacao foi encerrada com erro.
    pause
)

endlocal
