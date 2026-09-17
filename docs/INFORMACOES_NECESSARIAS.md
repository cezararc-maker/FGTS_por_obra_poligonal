# Informações e evidências necessárias antes da implementação

Este documento é o checklist oficial do projeto antes de qualquer código específico do FGTS Digital.

## 1. Decisões que o usuário precisa confirmar

### 1.1 Navegador

Confirmar:

- Google Chrome, Microsoft Edge ou outro Chromium;
- se podemos usar uma instância dedicada do navegador para a automação;
- se o login/certificado/procuração será realizado manualmente nessa instância;
- se a sessão permanecerá aberta enquanto a automação roda.

Recomendação atual: Chrome/Edge dedicado, visível, com perfil exclusivo da automação e depuração remota habilitada.

### 1.2 Formato exato da TAG

Fornecer um exemplo literal desejado.

Precisamos definir:

- ordem: código + nome ou nome + código;
- separador exato;
- espaços;
- caixa alta/baixa;
- acentos e caracteres especiais;
- limite máximo aceito pelo portal;
- regra se ultrapassar o limite.

Nenhum formato será inferido.

### 1.3 Estratégia para consignado

Ponto crítico: a documentação oficial atual mostra consignado dentro do fluxo da Guia Parametrizada e permite guia combinada com FGTS.

Precisamos confirmar se o objetivo é:

- A) gerar **uma GFD combinada** com FGTS + consignado por CNO quando houver;
- B) gerar **documentos/guias separados** por decisão operacional, se o portal permitir;
- C) outra regra.

Também confirmar se o relatório/detalhamento de consignado deve ser salvo separadamente quando o portal disponibilizar documento próprio.

### 1.4 Calendário de dias úteis

Para 08/2026 o vencimento 18/09/2026 decorre apenas do fim de semana e está definido.

Para competências futuras precisamos decidir a fonte usada para feriados/dias não úteis:

- calendário oficial aplicável ao FGTS;
- eventual tabela local de exceções;
- comportamento quando houver feriado local que não altere o vencimento federal.

A regra não será baseada apenas em uma biblioteca genérica de feriados sem validação.

## 2. Planilha de entrada

Enviar uma planilha modelo, preferencialmente com dados fictícios/mascarados, mas com a estrutura real.

Confirmar:

- nome da aba;
- linha do cabeçalho;
- nome exato da coluna CNO;
- nome exato da coluna Código da Obra;
- nome exato da coluna Nome da Obra;
- existência de linhas de totais ou cabeçalhos intermediários;
- se CNO vem pontuado ou apenas em dígitos;
- quantidade de dígitos esperada;
- se CNO pode começar com zero;
- se a mesma CNO pode aparecer legitimamente mais de uma vez;
- se deseja coluna opcional `PROCESSAR/IGNORAR` ou similar;
- se deseja que o resultado final seja exportado para uma nova planilha ou arquivo separado.

## 3. Evidência 1 — tela inicial da sessão representada

Enviar screenshot da tela completa logo após:

1. entrar no FGTS Digital;
2. selecionar a procuração/empresa correta;
3. chegar ao ponto em que você normalmente começa o processo.

Precisamos identificar:

- onde aparece a empresa/CNPJ representado;
- elemento confiável para validar que a sessão está na empresa correta;
- menu/caminho para Gestão de Guias;
- se existem avisos/banners que podem alterar o layout.

Pode mascarar CNPJ, razão social, CPF e demais dados sensíveis, desde que os rótulos/estrutura permaneçam visíveis.

## 4. Evidência 2 — acesso à Guia Parametrizada

Enviar screenshot da tela/menu usado para chegar à emissão parametrizada.

Precisamos saber:

- sequência manual exata de cliques;
- se abre nova rota/página/modal;
- qual texto/título confirma que a tela correta abriu.

Não precisamos da URL interna neste momento.

## 5. Evidência 3 — tela inicial do Passo 1 / pesquisa expandida

Enviar:

- screenshot da tela inteira;
- screenshot após expandir os filtros de pesquisa;
- descrição dos filtros que você preenche manualmente.

Precisamos identificar:

- competência inicial/final;
- tipo de débito;
- filtro por CNO;
- botão/ação de pesquisa;
- indicadores de carregamento.

## 6. Evidência 4 — qual filtro de CNO deve ser usado

A documentação atual admite CNO em diferentes contextos/filtros.

Enviar screenshot com o filtro correto destacado e informar:

- nome visual do filtro;
- por que esse é o filtro utilizado no seu procedimento;
- se sempre será o mesmo para todas as obras.

## 7. Evidência 5 — resultado da pesquisa por CNO

Executar manualmente uma pesquisa de teste e enviar screenshot.

Precisamos observar:

- tabela/listagem retornada;
- coluna em que aparece a CNO;
- código/nome da obra se aparecerem;
- quantidade de trabalhadores/débitos;
- paginação;
- estado sem resultado;
- estado com múltiplos resultados;
- estado de carregamento;
- qualquer aviso do portal.

## 8. Evidência 6 — seleção de trabalhadores/débitos FGTS

Enviar screenshots antes e depois de selecionar os itens.

Precisamos confirmar:

- checkbox/controle de seleção;
- se existe selecionar todos;
- se selecionar todos cobre todas as páginas ou somente a página atual;
- onde aparece a quantidade selecionada;
- se existem itens desabilitados;
- se há mistura de mensal/rescisório/outros débitos;
- como validar que todos os débitos desejados daquela CNO foram realmente incluídos.

## 9. Evidência 7 — Passo 2 / consignado

Enviar screenshot da tela imediatamente após avançar do FGTS.

Precisamos observar:

- mensagem que indica existência ou ausência de consignado;
- quantidade de trabalhadores, se exibida;
- se débitos já aparecem incluídos automaticamente;
- se é necessário pesquisar para visualizá-los;
- controles para adicionar/excluir;
- comportamento quando não existe consignado;
- comportamento quando existe consignado;
- se o seu objetivo é manter esses valores na mesma guia ou separá-los.

## 10. Evidência 8 — vencimento, TAG e resumo

Enviar screenshot da etapa em que aparecem:

- vencimento;
- TAG;
- totais FGTS;
- totais consignado;
- total geral;
- quantidade de trabalhadores/débitos se houver;
- ação de avançar.

Precisamos confirmar:

- formato aceito da data;
- se permite digitação direta;
- se o portal recalcula/limita a data;
- limite e validações da TAG;
- como reler/confirmar o valor efetivamente recebido pelo campo.

## 11. Evidência 9 — tela imediatamente anterior à emissão

Esta é a tela crítica para a confirmação humana.

Enviar screenshot completo e informar quais dados você costuma revisar manualmente.

Precisamos identificar:

- CNO/obra, se visível;
- competência;
- vencimento;
- TAG;
- total FGTS;
- total consignado;
- total geral;
- quantidade de trabalhadores;
- ação definitiva de emissão;
- eventual modal de confirmação.

A automação deverá parar aqui no primeiro teste.

## 12. Evidência 10 — pós-emissão

Após emitir manualmente uma guia de teste, enviar screenshots mostrando:

- estado de processamento;
- estado concluído;
- número/identificador da guia;
- situação da guia;
- botão/link para obter a guia;
- botões/ícones para detalhamento;
- PDF/CSV/relatórios disponíveis;
- como voltar para iniciar nova CNO.

Se existir espera assíncrona, informar aproximadamente como você percebe que terminou (spinner some, status muda, botão aparece etc.).

## 13. Evidência 11 — documentos baixados

Sem enviar documentos reais ao repositório público, informar:

- nomes originais dos arquivos baixados;
- extensão de cada arquivo;
- se o navegador baixa diretamente ou abre visualizador;
- se guia e relatório possuem nomes previsíveis;
- se o PDF detalhado corresponde ao que você chama de RE;
- se existe CSV adicional;
- se consignado gera relatório próprio.

Se necessário, pode enviar ao chat um exemplo totalmente anonimizado/mascarado apenas para análise, sem versioná-lo no GitHub público.

## 14. Casos especiais que precisamos observar ou decidir

Antes do lote, definir comportamento para:

- CNO não localizada;
- CNO sem débitos FGTS;
- CNO com FGTS mas sem consignado;
- CNO com consignado;
- CNO com consignado vencido;
- guia já emitida;
- pesquisa retorna mais de uma linha compatível;
- seleção parcial;
- portal indisponível;
- sessão expirada;
- CAPTCHA/MFA/autenticação adicional;
- modal inesperado;
- alteração de layout;
- erro após clicar para emitir;
- guia emitida mas download falhou;
- relatório não disponibilizado;
- intervenção manual que muda de página;
- navegador fechado acidentalmente;
- computador/internet interrompidos.

Política padrão proposta: **parar com erro controlado e nunca continuar silenciosamente**.

## 15. Informações para a interface

Confirmar preferências para:

- valor inicial das pausas humanas;
- confirmação antes de cada emissão: habilitada por padrão? (recomendação: SIM);
- botão Próxima CNO: exigir motivo?;
- Processada Manualmente: exigir observação?;
- Reprocessar CNO concluída: exigir dupla confirmação? (recomendação: SIM);
- pasta raiz padrão de saída ou escolha a cada execução;
- se deseja som/aviso visual quando entrar em pausa/erro.

## 16. Ordem recomendada de coleta

Para começarmos sem retrabalho, fornecer nesta ordem:

1. formato exato da TAG;
2. decisão FGTS + consignado (mesma guia ou separados);
3. navegador escolhido;
4. planilha modelo;
5. tela inicial da sessão/procuração;
6. caminho até Guia Parametrizada;
7. filtros expandidos e filtro correto por CNO;
8. resultado da CNO;
9. seleção dos débitos FGTS;
10. etapa de consignado;
11. vencimento/TAG;
12. pré-emissão;
13. pós-emissão;
14. downloads/detalhamentos.

## 17. Segurança ao coletar evidências

Não enviar ao repositório público:

- senha;
- certificado ou arquivo PFX/P12;
- cookie/token de sessão;
- CPF real de trabalhador;
- planilha operacional real;
- guia real;
- screenshots não mascarados com dados sensíveis.

Screenshots podem ser fornecidos no chat para análise e devem ser mascarados quando contiverem dados pessoais/sigilosos.
