@echo off
setlocal

set "CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME%" set "CHROME=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME%" set "CHROME=%LocalAppData%\Google\Chrome\Application\chrome.exe"

if not exist "%CHROME%" (
    echo [ERRO] Google Chrome nao encontrado nos caminhos padrao.
    echo Ajuste manualmente a variavel CHROME neste arquivo.
    pause
    exit /b 1
)

set "PROFILE=%LocalAppData%\FGTS_Poligonal\ChromeProfile"

if not exist "%PROFILE%" mkdir "%PROFILE%"

echo Abrindo Chrome dedicado para o teste...
echo Perfil: %PROFILE%
echo Porta de depuracao: 9222

echo.
echo IMPORTANTE:
echo 1. Faca o login no FGTS Digital manualmente.
echo 2. Selecione certificado/procuracao manualmente.
echo 3. Deixe o navegador aberto.
echo 4. Depois use o botao "Testar conexao com Chrome" no programa.
echo.

start "FGTS Poligonal - Chrome" "%CHROME%" --remote-debugging-port=9222 --user-data-dir="%PROFILE%" --start-maximized

endlocal
