# Fase 5 — Emissão e relatórios PDF

Objetivo: finalizar uma única guia já validada nas etapas anteriores.

Fluxo do teste:

1. Executa o fluxo validado até `Definir Vencimento`, com TAG preenchida.
2. Clica em `Emitir Guia`.
3. Aguarda o portal concluir o processamento e liberar os controles de relatório/reinício, com tolerância maior para o carregamento.
4. Clica em `Imprimir Relatório em PDF` do FGTS e aguarda o download.
5. Se existir relatório de Consignado, clica em `Imprimir Relatório em PDF` do Consignado e aguarda o download.
6. Se os downloads concluírem, clica em `Reiniciar` e retorna à Guia Parametrizada.

## Regra para download demorado

A automação usa uma janela curta de aproximadamente 5 segundos para detectar o início/conclusão do download controlado. Se o relatório não concluir nessa janela, a interface informa qual relatório ficou pendente e pergunta ao operador:

- **SIM**: continuar para a próxima guia. A automação tenta `Reiniciar` e registra `DOWNLOAD NÃO CONCLUÍDO` para aquele relatório.
- **NÃO**: permanecer na guia atual para conferência ou download manual. A automação não reinicia o fluxo.

## Estados de relatório

- `CONCLUÍDO`
- `NÃO HÁ CONSIGNADO`
- `DOWNLOAD NÃO CONCLUÍDO`

## Pasta de teste

Enquanto o comportamento real dos downloads está sendo validado, os PDFs controlados são salvos localmente em:

`downloads/<competência>/<inscrição>/`

A pasta `downloads` é local de execução e não deve ser versionada no repositório.

## Segurança

- somente uma inscrição por teste nesta fase;
- nenhuma repetição automática de emissão para a mesma inscrição;
- em qualquer erro não relacionado ao timeout controlado de download, a automação para;
- screenshots de erro permanecem somente no computador local.
