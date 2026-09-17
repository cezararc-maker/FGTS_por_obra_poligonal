# Referências oficiais e técnicas

Referências consultadas na fase de arquitetura. Elas servem para validar regras e possibilidades técnicas, mas **não substituem o levantamento da interface real** para definição de seletores, estados e validações.

## FGTS Digital — página oficial

- Ministério do Trabalho e Emprego — FGTS Digital:
  https://www.gov.br/trabalho-e-emprego/pt-br/servicos/empregador/fgtsdigital

- Manual e Documentação Técnica:
  https://www.gov.br/trabalho-e-emprego/pt-br/servicos/empregador/fgtsdigital/manual-e-documentacao-tecnica

Na data desta análise, a página oficial lista o **Manual do FGTS Digital — versão 1.70, de 12/06/2026**.

## Manual do FGTS Digital — versão 1.70

- Ministério do Trabalho e Emprego — Manual de Orientação do FGTS Digital, versão 1.70, de 12/06/2026:
  https://www.gov.br/trabalho-e-emprego/pt-br/servicos/empregador/fgtsdigital/manual-e-documentacao-tecnica/manual-de-orientacao-do-fgts-digital-versao-1-70-12-06-2026.pdf

O manual atual documenta o fluxo da Guia Parametrizada e o tratamento de débitos de FGTS e consignado.

## Perguntas Frequentes — FGTS Digital

- Ministério do Trabalho e Emprego — Perguntas Frequentes:
  https://www.gov.br/trabalho-e-emprego/pt-br/servicos/empregador/fgtsdigital/perguntas-frequentes

As FAQs oficiais registram que a Guia Parametrizada possui etapa específica para débitos consignados e que esses valores podem compor a mesma guia juntamente com FGTS.

## Relatórios/detalhamentos

A documentação do FGTS Digital descreve opções de detalhamento e relatórios em PDF/CSV associados às guias. A automação só deverá implementar esses downloads depois de confirmar os controles reais na interface em uso.

## Lei nº 8.036/1990

- Presidência da República / Planalto — Lei nº 8.036/1990, texto compilado:
  https://www.planalto.gov.br/ccivil_03/leis/l8036compilada.htm

O projeto manterá a regra de vencimento desacoplada da interface, com validação específica do calendário aplicável.

## Playwright — conexão a navegador Chromium existente

- Documentação oficial do Playwright para Python — `BrowserType.connect_over_cdp`:
  https://playwright.dev/python/docs/api/class-browsertype#browser-type-connect-over-cdp

A documentação informa que a conexão por CDP funciona apenas com navegadores baseados em Chromium e possui fidelidade inferior ao protocolo nativo do Playwright. Portanto, será usada somente após validação das funções críticas no ambiente real.

## Chrome — depuração remota

- Chrome for Developers — Changes to remote debugging switches to improve security:
  https://developer.chrome.com/blog/remote-debugging-port

Desde o Chrome 136, os parâmetros de depuração remota não são respeitados quando apontam para o diretório padrão de dados do Chrome. É necessário usar um `--user-data-dir` não padrão. Isso reforça a arquitetura com um perfil dedicado da automação, separado do perfil principal do usuário.

## Regra de projeto

Nenhuma documentação, screenshot de manual ou conhecimento prévio será usado para inventar seletores CSS/XPath, URLs internas ou comportamento de telas. Para cada etapa real do portal serão coletados:

- estado esperado antes da ação;
- elemento real;
- ação realizada;
- estado verificável após a ação;
- comportamento em falha.
