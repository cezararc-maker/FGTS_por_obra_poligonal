@echo off
setlocal
cd /d "%~dp0.."

if not exist ".venv\Scripts\python.exe" (
    echo [ERRO] Ambiente virtual nao encontrado.
    echo Execute primeiro scripts\instalar_teste.bat
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m fgts_obra.app_fase6

if errorlevel 1 (
    echo.
    echo [ERRO] A aplicacao terminou com codigo de erro.
    pause
)

endlocal
