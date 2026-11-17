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

rem Nunca reutiliza perfil: cookies, cache, extensoes e preferencias da sessao
rem anterior nao interferem na proxima emissao.

netstat -ano | findstr /r /c:":9222 .*LISTENING" >nul

if not errorlevel 1 (
    echo A porta do Chrome dedicado (9222) ja esta em uso.
    echo Feche somente essa janela antes de abrir uma nova sessao limpa.
    echo Nenhum navegador pessoal foi fechado.
    pause
    exit /b 0
)

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

start "FGTS Poligonal - Chrome" "%CHROME%" --remote-debugging-port=9222 --user-data-dir="%PROFILE%" --no-first-run --no-default-browser-check --disable-sync --disable-extensions --start-maximized "https://fgtsdigital.sistema.gov.br/cobranca/"

endlocal
