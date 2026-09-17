# Fase 4 — Consignado, vencimento e TAG

## Objetivo

Validar o trecho posterior a `Adicionar à guia`, ainda com uma única inscrição e sem emitir guia.

## Fluxo permitido

1. Executar o fluxo já validado até `Adicionar à guia`.
2. Clicar em `Avançar`.
3. Aguardar `Selecionar Débitos Consignado`.
4. Não alterar a seleção dos débitos consignados; o portal já os seleciona automaticamente de acordo com os CPFs escolhidos na etapa FGTS.
5. Clicar em `Avançar` novamente.
6. Aguardar `Definir Vencimento`.
7. Conferir se o vencimento exibido pelo portal coincide com o vencimento calculado pelo programa.
8. Preencher a TAG exatamente como está na planilha.
9. Parar antes de `Emitir Guia`.

## Bloqueios

- não marcar/desmarcar débitos consignados;
- não alterar manualmente o vencimento nesta fase;
- não clicar em `Emitir Guia`;
- não baixar documentos;
- não reiniciar o fluxo.

## Observação

Se a estrutura do campo TAG ou da etapa de vencimento não for identificada com segurança, a automação deve interromper e gerar screenshot local para calibração. Nenhum seletor deve ser adivinhado com cliques cegos.
