# FGTS por Obra / Poligonal

Automação **assistida** em Python para geração individualizada de guias no FGTS Digital por CNO/obra.

> Status: **Fase 0 — arquitetura e levantamento da interface**.
>
> O projeto não implementará cliques, seletores, URLs ou comportamentos específicos do portal sem evidência da interface real e atual.

## Princípios do projeto

- GitHub é a fonte oficial do código e da documentação.
- Navegador sempre visível durante a execução.
- A sessão do FGTS Digital deve estar previamente autenticada pelo usuário.
- O projeto não obtém, armazena ou manipula senhas ou certificados digitais.
- Pausas configuráveis entre etapas.
- Controle de **Pausar**, **Retomar** e **Abortar**.
- Em erro ou estado inesperado, a execução para com identificação de CNO, obra e etapa.
- Retomada somente após revalidação do estado da tela; nunca continuar às cegas após intervenção manual.
- Logs estruturados e captura de evidência em falhas.
- Competência parametrizada; primeiro cenário de teste: `08/2026`.
- Dados reais, PDFs, planilhas operacionais, screenshots com informações sensíveis e logs de execução não devem ser versionados.

## Cenário inicial

Entrada mínima prevista em Excel:

- CNO
- Código da obra
- Nome da obra

Antes da execução haverá duas confirmações humanas:

1. confirmação da competência/período;
2. confirmação do resumo final, incluindo competência, vencimento calculado, quantidade de CNOs e empresa identificada quando possível.

Para a competência `08/2026`, o vencimento mensal esperado é `18/09/2026`, pois `20/09/2026` é domingo e o vencimento deve ser antecipado para o dia útil imediatamente anterior.

## Arquitetura proposta

A proposta técnica e os pontos ainda pendentes de evidência estão documentados em `docs/ARQUITETURA.md` e `docs/INFORMACOES_NECESSARIAS.md`.

## Regra de implementação do portal

Nenhum seletor específico do FGTS Digital será criado por adivinhação. Antes de codificar o fluxo web, cada etapa relevante deverá ser confirmada por evidência atual do portal (captura de tela e, preferencialmente, identificação estrutural do DOM/HTML sem dados sensíveis).
