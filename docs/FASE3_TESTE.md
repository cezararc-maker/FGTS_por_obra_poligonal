# Modo TESTE — Fase 3

## Objetivo

Validar, para uma única inscrição por execução, o trecho imediatamente posterior à pesquisa de débitos no FGTS Digital.

A Fase 3:

1. navega até Emissão de Guia Parametrizada;
2. seleciona competência Inicial e Final;
3. desmarca Vencido;
4. abre Pesquisa Expandida;
5. seleciona CNPJ ou CNO em Estabelecimento da Remuneração;
6. preenche a inscrição;
7. executa Pesquisar;
8. reconhece a grade real de Seleção de Débitos sem pressupor tag HTML `<table>`;
9. marca o checkbox geral da grade;
10. aciona `Adicionar à guia`;
11. para obrigatoriamente antes de `Avançar`.

## Limite de segurança

Nesta fase é proibido clicar em `Avançar`, entrar em Selecionar Débitos Consignado, definir vencimento/TAG, emitir guia ou baixar documentos.

## Execução no Windows

Com a branch `feat/modo-teste-fase3` ativa e o ambiente virtual já instalado:

```bat
scripts\executar_teste_fase3.bat
```

O Chrome dedicado deve estar aberto por `scripts\abrir_chrome_teste.bat` e autenticado manualmente no FGTS Digital.

## Resultado esperado

Após `Adicionar à guia`, a aplicação deve mostrar uma mensagem de conclusão e permanecer na etapa `Selecionar Débitos FGTS`. O operador deve conferir visualmente se o resumo/valor da guia foi atualizado. A automação não deve clicar em `Avançar`.

## Em caso de erro

A execução é interrompida e uma screenshot local é gravada na pasta `screenshots/`, que não deve ser versionada no repositório público.
