@echo off
setlocal
cd /d "%~dp0\.."

if not exist ".venv\Scripts\python.exe" (
    echo [ERRO] Ambiente virtual nao encontrado.
    echo Execute primeiro scripts\instalar_teste.bat
    pause
    exit /b 1
)

call ".venv\Scripts\activate.bat"
python -m fgts_obra.app

if errorlevel 1 (
    echo.
    echo [ERRO] A aplicacao foi encerrada com erro.
    pause
)

endlocal
