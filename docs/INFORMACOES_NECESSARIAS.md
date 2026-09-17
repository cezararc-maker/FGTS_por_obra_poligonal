# Informações necessárias antes de implementar o fluxo do portal

Este documento separa o que já está definido do que ainda precisa ser confirmado com evidência real.

## 1. Navegador e conexão à sessão autenticada

Confirmar:

- navegador utilizado na operação: Chrome, Edge ou outro Chromium;
- se podemos iniciar uma instância dedicada do navegador com depuração remota habilitada;
- se o login/certificado/procuração será realizado manualmente nessa mesma instância antes de iniciar o Python;
- se haverá mais de uma empresa/procuração na mesma sessão.

Objetivo: controlar uma sessão visível sem manipular senha ou certificado.

## 2. Planilha de entrada

Precisamos de uma planilha modelo, preferencialmente com dados fictícios ou mascarados, contendo o mesmo layout da planilha real.

Confirmar:

- nome da aba;
- linha do cabeçalho;
- nome exato da coluna de CNO;
- nome exato da coluna de código da obra;
- nome exato da coluna de nome da obra;
- se existem linhas de totais/cabeçalhos intermediários;
- se CNO vem com pontuação ou apenas dígitos;
- se o CNO pode começar com zero;
- se a mesma CNO pode aparecer mais de uma vez;
- se haverá coluna com status como `PROCESSAR`, `IGNORAR`, `CONCLUÍDO` etc.

## 3. Formato exato da TAG

Ainda não definido e não será inventado.

Precisamos confirmar:

- ordem: código + nome ou nome + código;
- separador exato;
- exemplo real de TAG desejada;
- uso de espaços;
- caixa alta/baixa;
- limite máximo aceito pelo portal;
- o que fazer quando o texto ultrapassar o limite;
- tratamento de acentos e caracteres especiais.

Exemplo de decisão que o usuário deverá fornecer futuramente, sem assumir que seja o padrão real:

```text
CODIGO - NOME DA OBRA
```

## 4. Caminho até Emissão de Guia Parametrizada

Precisamos de evidência atual do portal mostrando:

- página/tela em que a automação começará depois que o usuário estiver logado;
- menu ou botão usado para chegar à Guia Parametrizada;
- como confirmar estruturalmente que a página correta abriu.

Idealmente enviar screenshot da tela completa e, quando começarmos a implementação, evidência do DOM/HTML do elemento-alvo.

## 5. Competência de apuração

A documentação oficial indica campos `Inicial` e `Final` na pesquisa da Guia Parametrizada.

Precisamos confirmar na interface atual:

- formato aceito pelo campo;
- se o campo permite digitação direta;
- se existe máscara;
- se o valor deve ser limpo antes;
- qual feedback indica que o portal aceitou a competência.

Para o primeiro teste os dois campos deverão resultar em `08/2026`.

## 6. Qual filtro de CNO será usado

A documentação atual do FGTS Digital apresenta mais de um contexto que admite CNO, como estabelecimento da remuneração, tomador de serviços e local de trabalho.

Portanto, precisamos confirmar **qual deles representa exatamente o filtro que você usa manualmente para separar a obra**.

Enviar screenshot com a opção correta indicada.

Não será implementada escolha automática entre esses filtros sem essa confirmação.

## 7. Pesquisa e resultado da CNO

Precisamos observar uma pesquisa real ou mascarada para entender:

- botão exato que executa a pesquisa;
- mensagem de carregamento;
- estrutura da tabela de resultados;
- coluna em que a CNO aparece;
- como o portal representa CNO sem resultado;
- como representa mais de um resultado;
- paginação;
- como confirmar que a CNO exibida é exatamente a solicitada.

## 8. Seleção dos colaboradores/débitos

Este é um ponto crítico.

Precisamos confirmar:

- onde fica o checkbox de seleção;
- se existe `selecionar todos`;
- se `selecionar todos` seleciona somente a página visível ou todos os resultados da pesquisa;
- como identificar a quantidade total de trabalhadores/débitos;
- se há paginação;
- se existem registros não selecionáveis;
- se a seleção inclui FGTS mensal, rescisório ou ambos;
- qual estado visual/DOM confirma que todos os itens desejados foram selecionados.

A automação não avançará apenas porque um checkbox foi clicado; deverá existir validação da seleção.

## 9. Etapa intermediária de débitos consignados

A documentação atual indica que o fluxo da Guia Parametrizada pode possuir uma etapa específica de débitos consignados.

Precisamos confirmar como deve ser tratada no seu processo:

- deve incluir consignado junto com o FGTS daquela CNO;
- deve excluir/ignorar consignado;
- deve apenas avançar sem seleção;
- existem competências/empresas sem essa etapa relevante.

Esse comportamento não será presumido.

## 10. Tela de vencimento e TAG

Precisamos de screenshot da etapa em que aparecem:

- vencimento da guia;
- TAG;
- totais;
- botão para avançar.

Confirmar:

- se a data é digitável ou escolhida por calendário;
- formato da data;
- se o portal altera automaticamente uma data informada;
- como validar pelo DOM o valor efetivamente recebido;
- limite e validações do campo TAG.

## 11. Emissão final da guia

A solicitação recebida termina em `Depois de preencher...`, então a parte final do comportamento ainda precisa ser enviada.

Precisamos definir:

- qual é a última ação humana/automática antes da emissão;
- se a automação deverá clicar em `Emitir Guia`;
- se haverá uma confirmação/modal final;
- se deverá baixar PDF;
- se deverá baixar algum relatório/CSV adicional;
- pasta de saída;
- padrão de nome do arquivo;
- se deve renomear o PDF usando código/nome/CNO;
- como confirmar que o download terminou;
- se deverá voltar à tela inicial da Guia Parametrizada para processar a próxima CNO;
- o que fazer se a guia já tiver sido emitida anteriormente.

## 12. Empresa da sessão

O resumo inicial deve exibir a empresa encontrada no portal quando possível.

Precisamos confirmar:

- onde o portal mostra Razão Social/CNPJ da empresa representada;
- se esse dado permanece visível durante todo o fluxo;
- se deseja apenas exibir ou também comparar com algum CNPJ esperado da planilha/configuração;
- comportamento se a empresa não puder ser identificada com segurança.

Recomendação de segurança: se houver um CNPJ esperado configurado, bloquear o processamento quando o portal mostrar empresa diferente.

## 13. Comportamento em situações especiais

Definir antes do primeiro teste amplo:

- CNO não encontrada;
- CNO encontrada, mas sem débitos;
- alguns trabalhadores sem débito selecionável;
- guia já emitida;
- portal retorna erro;
- sessão expira;
- portal exige nova autenticação;
- página muda de layout;
- popup/modal inesperado;
- download falha;
- usuário intervém manualmente e muda de página;
- duplicidade de CNO na planilha.

A política padrão proposta é **parar com erro controlado**, nunca pular silenciosamente.

## 14. Evidências recomendadas

Para cada etapa do portal, o ideal é fornecer:

1. screenshot da tela completa;
2. screenshot aproximado do elemento relevante;
3. descrição do que você faz manualmente;
4. quando iniciarmos a codificação, HTML/DOM mínimo do elemento ou informações de acessibilidade obtidas por ferramenta de inspeção.

Não enviar ao GitHub público:

- certificado;
- cookie de sessão;
- token;
- senha;
- CPF de trabalhador;
- planilha operacional real;
- PDF real de guia;
- screenshots com dados sensíveis sem mascaramento.

## 15. Ordem recomendada para o levantamento

Para reduzir retrabalho, coletar as telas nesta ordem:

1. tela inicial após login/procuração;
2. entrada em Gestão de Guias / Guia Parametrizada;
3. pesquisa expandida;
4. filtro correto por CNO;
5. resultado da pesquisa;
6. seleção de todos os débitos/trabalhadores;
7. avanço e eventual etapa de consignado;
8. vencimento + TAG;
9. tela imediatamente anterior à emissão;
10. resultado após emissão/download.
