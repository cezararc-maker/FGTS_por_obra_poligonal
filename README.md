# FGTS por Obra / Poligonal

Automação assistida em Python para geração de Guias Parametrizadas no FGTS Digital por CNPJ/CNO, com processamento em lote, downloads organizados por TAG, checkpoint local e compactação final da competência.

## Estado do projeto

Versão consolidada para uso mensal: **1.0.0**.

O fluxo foi validado no portal real com emissão, download da guia, relatório FGTS, relatório Consignado quando disponível, reinício entre inscrições, lote sequencial e geração do ZIP da competência.

## Princípios

- GitHub é a fonte oficial do código.
- O Chrome permanece visível durante a execução.
- A autenticação no FGTS Digital é sempre feita manualmente pelo operador.
- O programa não armazena senhas, certificados, cookies ou credenciais.
- Em estado inesperado, a automação interrompe o lote em vez de clicar por aproximação.
- PDFs, planilhas operacionais, screenshots e checkpoints locais não são versionados.

## Requisitos

- Windows 10 ou 11;
- Python 3.11;
- Google Chrome;
- Git;
- acesso ao FGTS Digital com sessão previamente autenticada.

## Instalação

No PowerShell, dentro do repositório:

```powershell
.\scripts\instalar.bat
```

O instalador prepara o `.venv` e as dependências do projeto.

## Abrir o Chrome dedicado

No painel principal, use **Abrir Chrome dedicado**. Também é possível abrir em um PowerShell separado:

```powershell
.\scripts\abrir_chrome.bat
```

O Chrome dedicado abre diretamente `https://fgtsdigital.sistema.gov.br/cobranca/`. Se o portal redirecionar para autenticação, conclua-a manualmente.

No Chrome aberto pelo script:

1. confirme que o FGTS Digital abriu;
2. faça a autenticação/certificado manualmente;
3. assuma a procuração/empresa, quando necessário;
4. deixe a sessão aberta.

## Importação direta do Leitor de Extrato

Abra `ABRIR_LEITOR_FGTS.bat` no repositório irmão `Leitor_PDF_Extrato_Mensal_Poligonal`. Depois de processar o PDF, **Exportar para FGTS por Obra** salva uma cópia validada do XLSX em Downloads e abre este painel com a planilha carregada. A ponte usa somente `127.0.0.1`, porta temporária e token da sessão; não acessa o portal nem emite guias automaticamente. O botão **Baixar XLSX** do leitor continua funcionando separadamente.

## Executar a aplicação

```powershell
.\scripts\executar.bat
```

A interface principal permite:

- selecionar e validar a planilha;
- ordenar as inscrições clicando nos cabeçalhos (cliques alternam entre ordem crescente e decrescente);
- selecionar uma ou várias inscrições com `Ctrl + clique`, ou um intervalo com `Shift + clique`;
- usar **Selecionar todas as pendentes** sem iniciar a emissão;
- usar **Gerar todas as pendentes** para selecionar somente inscrições sem processamento registrado e abrir a confirmação antes do lote;
- conferir a seleção antes da emissão;
- gerar guias em sequência;
- solicitar `Parar após a atual` para terminar a inscrição em andamento;
- usar **Parar imediatamente** para encerrar apenas a automação em andamento, mantendo o painel e o Chrome abertos; a inscrição interrompida fica para conferência no portal antes de qualquer repetição;
- mostrar na primeira coluna o estado de cada inscrição, incluindo PDF da guia e relatório FGTS registrados;
- atualizar as situações pelo botão **Atualizar situações**;
- registrar manualmente um PDF de guia recuperada sem marcar relatórios ou lote como concluídos;
- indicar **Não há débitos** após uma pesquisa sem resultados, seguindo o lote sem emitir guia nem criar pasta para essa inscrição;
- impedir repetição de inscrições já concluídas ou com emissão pendente de conferência no checkpoint;
- gerar manualmente o ZIP da competência.

## Fluxo operacional

Para cada inscrição selecionada, a aplicação:

1. abre `Gestão de Guias > Emissão de Guia Parametrizada`;
2. seleciona a competência inicial e final;
3. confere o filtro `Vencido`;
4. abre a pesquisa expandida;
5. pesquisa CNPJ/CNO em `Estabelecimento da Remuneração`;
6. seleciona os débitos e adiciona à guia;
7. avança pelo Consignado sem alterar manualmente a seleção automática do portal;
8. valida o vencimento;
9. preenche a TAG normalizada na importação da planilha (caracteres não aceitos são removidos e o ajuste aparece no painel);
10. emite a guia;
11. confirma a emissão pelo número dinâmico e/ou estado final do portal;
12. salva a própria guia e os relatórios;
13. reinicia o fluxo para a próxima inscrição.

## Pasta de saída

Os arquivos são salvos diretamente em:

```text
%USERPROFILE%\Downloads\FGTS_por_obra_poligonal\<MM-AAAA>\<TAG>\
```

Exemplo:

```text
C:\Users\<usuario>\Downloads\FGTS_por_obra_poligonal\08-2026\
  89-CRECHE E E. ED INFANTIL 900272665773\
    <nome original da guia>.pdf
    <nome original do relatório FGTS>.pdf
    <nome original do relatório Consignado>.pdf
```

Os nomes originais fornecidos pelo portal são preservados, exceto por substituição de caracteres inválidos para o Windows.

## Checkpoint

O controle persistente fica na pasta da competência:

```text
%USERPROFILE%\Downloads\FGTS_por_obra_poligonal\<MM-AAAA>\controle_lote.json
```

Inscrições marcadas como `CONCLUIDO`, `CONFERIR_EMISSAO`, `GUIA_RECUPERADA`, `PROCESSANDO` ou com relatório pendente não são reemitidas automaticamente. Se a conexão com o Chrome falhar após o início da emissão, confira a guia no portal antes de nova tentativa. Para uma guia já emitida e recuperada pelo operador, selecione uma inscrição no painel e use **Registrar guia recuperada** para indicar o PDF. Esse registro não confirma os relatórios nem encerra o lote. Se a inscrição estiver como **Em processamento; conferir se parou** ou **Conferir emissão; NÃO repetir**, selecione somente ela e use **Conferi: guia não encontrada** após verificar no portal que não houve emissão. A confirmação libera uma nova tentativa e fica registrada no controle local. O checkpoint e os PDFs são locais; `git pull` não os sincroniza entre máquinas.

## ZIP da competência

O botão `Gerar ZIP da competência` compacta **somente as subpastas das TAGs existentes dentro da pasta da competência atual**.

Para `08/2026`, o arquivo gerado é:

```text
Guias de FGTS por Obra 082026.zip
```

O ZIP não inclui:

- arquivos soltos da pasta geral `Downloads`;
- `controle_lote.json`;
- o próprio ZIP;
- arquivos de outra competência.

Quando todos os registros da planilha constarem como concluídos no checkpoint e o lote terminar sem erros/pendências, a aplicação também tenta gerar o ZIP automaticamente.

## Segurança operacional

- O clique em `Emitir Guia` usa prova de estabilidade antes da ação real.
- A automação não usa `force=True` para contornar estados instáveis.
- O lote é interrompido em erro inesperado.
- `Parar após a atual` termina a inscrição em andamento antes de encerrar o lote.
- Em falha/atraso de relatório, o operador decide se continua ou permanece na guia atual.

## Testes locais

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Os testes cobrem regras de competência/vencimento, leitura da planilha, espera da grade após carregamento, organização da pasta de saída e escopo do ZIP. O fluxo de setembro de 2026 foi testado e validado pelo operador em 15/10/2026. Mudanças futuras devem ser conferidas antes de uso em lote.

## Estrutura relevante

```text
src/fgts_obra/
  app_final.py          # interface principal
  production_flow.py    # orquestração de produção
  portal_flow.py        # navegação base no portal
  phase3_flow.py        # seleção de débitos validada
  phase4_flow.py        # consignado/vencimento/TAG validados
  phase5_flow.py        # emissão/download validados
  phase6_flow.py        # organização e ZIP
  batch_state.py        # checkpoint

scripts/
  executar.bat
  abrir_chrome.bat
  instalar.bat
```

As antigas entradas das fases de teste foram retiradas; permanecem no histórico Git. A entrada oficial é `scripts\executar.bat`.

## Dados sensíveis

O repositório é público. Nunca versionar planilhas reais, PDFs de guias, screenshots operacionais, logs com dados pessoais, cookies/tokens, certificados PFX/P12 ou credenciais.
