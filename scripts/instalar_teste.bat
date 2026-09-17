@echo off
setlocal
cd /d "%~dp0\.."

if not exist ".venv\Scripts\python.exe" (
    py -3.11 -m venv .venv
    if errorlevel 1 (
        echo [ERRO] Nao foi possivel criar o ambiente virtual com Python 3.11.
        pause
        exit /b 1
    )
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 goto :erro
python -m pip install -e .
if errorlevel 1 goto :erro

echo.
echo [OK] Ambiente de teste instalado.
echo Use scripts\executar_teste.bat para abrir a aplicacao.
pause
exit /b 0

:erro
echo.
echo [ERRO] Falha durante a instalacao do ambiente de teste.
pause
exit /b 1
