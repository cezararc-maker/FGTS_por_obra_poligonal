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

set "PROFILE_ROOT=%LocalAppData%\FGTS_Poligonal\ChromeSessoes"

if not exist "%PROFILE_ROOT%" mkdir "%PROFILE_ROOT%"

set "PROFILE=%PROFILE_ROOT%\sessao_%RANDOM%_%RANDOM%"
mkdir "%PROFILE%"

echo Abrindo Chrome dedicado para o FGTS Digital...
echo Perfil temporario e limpo: %PROFILE%
echo Porta de depuracao: 9222

echo.
echo IMPORTANTE:
echo 1. Faca o login no FGTS Digital manualmente.
echo 2. Selecione certificado/procuracao manualmente.
echo 3. Use este navegador somente para gerar guias e deixe-o aberto durante o lote.
echo 4. Depois use o botao "Testar conexao com Chrome" no programa.
echo.

start "" "%CHROME%" --remote-debugging-port=9222 --user-data-dir="%PROFILE%" --no-first-run --no-default-browser-check --disable-sync --disable-extensions --start-maximized "https://fgtsdigital.sistema.gov.br/cobranca/"

endlocal
