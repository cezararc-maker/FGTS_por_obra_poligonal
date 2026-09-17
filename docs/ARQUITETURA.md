# Arquitetura aprovada para análise — ainda sem implementação

## 1. Objetivo

Construir uma automação **assistida** em Python para geração de guias individualizadas no FGTS Digital por CNO/obra, mantendo o operador no controle da execução e utilizando uma sessão de navegador previamente autenticada.

Princípios obrigatórios:

- navegador sempre visível;
- nenhuma manipulação de senha, certificado, MFA, CAPTCHA ou credencial;
- pausas humanas configuráveis;
- espera preferencial por estados/elementos reais do portal;
- pausa, retomada e encerramento controlados;
- nenhuma continuidade silenciosa após falha;
- rastreabilidade por CNO, obra e etapa;
- primeira execução obrigatoriamente em modo TESTE com uma única CNO;
- seletores, URLs e nomes de elementos do portal somente após evidência real.

## 2. Decisão tecnológica

### Python

Python será a linguagem principal.

### Playwright em vez de Selenium

Recomendação: **Playwright para Python**.

Motivos principais:

- esperas e locators mais adequados a aplicações web dinâmicas;
- melhor controle de navegação e mudanças de estado;
- suporte consistente a downloads;
- inspeção estrutural do DOM antes e depois de ações;
- screenshots/traces úteis para diagnóstico;
- possibilidade de conexão a navegador Chromium visível por CDP quando preparado para isso.

Selenium continua tecnicamente possível, mas não oferece vantagem relevante para este projeto. A prioridade aqui é previsibilidade, validação do estado da página e download controlado.

### Observação sobre navegador já autenticado

A estratégia preferida não será tentar anexar a automação a qualquer janela comum do Chrome já aberta. O fluxo planejado é:

1. iniciar uma instância **dedicada e visível** do Chrome/Edge/Chromium com perfil exclusivo da automação e depuração remota habilitada;
2. o usuário realiza login, certificado digital e procuração manualmente nessa janela;
3. somente depois o Python conecta à sessão visível;
4. a automação nunca recebe nem armazena senha ou certificado.

Chrome moderno exige diretório de perfil não padrão para depuração remota. Portanto, o perfil da automação deverá ser isolado do perfil principal do usuário.

A conexão por CDP possui fidelidade inferior ao protocolo nativo do Playwright; por isso, todas as funcionalidades críticas serão validadas no teste real antes do processamento em lote.

## 3. Camadas do projeto

A implementação futura será separada em seis responsabilidades.

### A. Interface do operador

Responsável por:

- selecionar Excel;
- informar competência;
- mostrar vencimento calculado;
- mostrar quantidade de CNOs;
- mostrar empresa identificada no portal, quando possível;
- exibir log em tempo real;
- exibir CNO/obra/etapa atual;
- PAUSAR;
- RETOMAR;
- PARAR/ENCERRAR;
- PRÓXIMA CNO;
- REPROCESSAR CNO;
- marcar PROCESSADA MANUALMENTE;
- controlar modo TESTE;
- habilitar/desabilitar confirmação antes da emissão.

Interface inicial recomendada: **Tkinter/ttk**, sem framework web ou interface complexa.

### B. Domínio e validações

Responsável por:

- competência;
- período inicial/final;
- cálculo de vencimento;
- validação da planilha;
- CNO;
- código/nome da obra;
- formatação da TAG;
- regras de status.

Essa camada não conhecerá o navegador.

### C. Orquestrador da execução

Responsável por:

- fila de CNOs;
- modo TESTE ou lote;
- máquina de estados;
- checkpoints;
- pausa/retomada;
- política de erro;
- reprocessamento;
- pular CNO por comando explícito;
- impedir duplicidade de emissão.

### D. Adaptador do FGTS Digital

Responsável exclusivamente pela interação com o portal.

Será dividido conceitualmente por páginas/etapas e usará seletores centralizados. Nenhum seletor será distribuído aleatoriamente pelo código.

O adaptador só será desenvolvido após o levantamento da interface real.

### E. Persistência, auditoria e recuperação

Recomendação:

- **SQLite** (biblioteca padrão `sqlite3`) como estado durável da execução;
- arquivo `.log` legível em tempo real;
- registro estruturado por evento;
- screenshots locais em falha;
- exportação de resultado final para XLSX/CSV.

SQLite é preferível a usar um Excel aberto como banco de estado durante a execução: reduz risco de bloqueio/corrupção e facilita retomada, reprocessamento e consulta de CNOs.

### F. Gerenciador de artefatos/downloads

Responsável por:

- detectar início/fim de download;
- classificar documento recebido;
- renomear de forma segura somente após confirmação do tipo;
- mover para pasta da CNO;
- registrar caminho e hash/tamanho quando útil;
- impedir que um download ausente seja tratado como sucesso.

A estrutura final de pastas só será fixada depois de confirmarmos quais documentos o portal realmente fornece em cada etapa.

## 4. Bibliotecas sugeridas

Dependências principais previstas:

- `playwright`: automação do navegador;
- `openpyxl`: leitura e exportação de Excel;
- `pandas`: opcional, apenas se simplificar validações/relatórios;
- `tkinter`/`ttk`: interface local (já acompanha a instalação padrão do Python em muitos ambientes Windows);
- `sqlite3`: checkpoint/estado persistente;
- `logging`: log textual;
- `pathlib`, `datetime`, `threading`, `queue`, `json`, `hashlib`: biblioteca padrão.

Não é necessário introduzir banco externo, servidor web ou API externa na primeira versão.

## 5. Fluxo antes de qualquer CNO

1. abrir aplicação;
2. selecionar planilha;
3. validar cabeçalhos e linhas;
4. informar competência;
5. calcular período e vencimento;
6. mostrar primeira confirmação de competência/período;
7. conectar à sessão autenticada visível;
8. identificar empresa no portal se houver elemento confiável;
9. mostrar resumo final:
   - competência;
   - vencimento;
   - quantidade de CNOs válidas;
   - empresa encontrada;
   - modo TESTE/lote;
10. exigir confirmação SIM antes de qualquer processamento.

## 6. Validação da planilha

A leitura deverá preservar CNO e código como texto.

Bloqueios antes do início:

- CNO vazio;
- CNO com formato inválido;
- duplicidade não autorizada;
- código da obra vazio;
- nome da obra vazio;
- cabeçalhos ausentes;
- linhas conflitantes para a mesma CNO.

O operador deverá receber uma lista de inconsistências e a execução não começará enquanto existirem erros bloqueantes.

Ainda precisamos confirmar a regra exata de validade/formatação do CNO e se a planilha poderá possuir uma coluna de controle.

## 7. Competência e vencimento

A competência será parâmetro de execução e nunca hardcoded.

Para o primeiro teste:

- competência: `08/2026`;
- período inicial: `08/2026`;
- período final: `08/2026`;
- data-base: `20/09/2026`;
- vencimento esperado: `18/09/2026`.

O mecanismo de calendário deverá ser isolado e testável. Para competências futuras, será necessário definir explicitamente qual calendário oficial de dias não úteis deverá ser usado além de fins de semana.

## 8. TAG

A TAG será função isolada e testável, mas **não será implementada até o usuário definir o formato exato**.

Precisamos saber:

- ordem de código/nome;
- separador;
- espaços;
- caixa alta/baixa;
- limite máximo aceito;
- regra de truncamento;
- acentos/caracteres especiais.

## 9. Máquina de estados por CNO

Estados conceituais previstos:

- AGUARDANDO;
- INICIANDO_CNO;
- ACESSANDO_GUIA_PARAMETRIZADA;
- CONFIGURANDO_FILTROS;
- PESQUISANDO_CNO;
- VALIDANDO_CNO;
- SELECIONANDO_DEBITOS_FGTS;
- VALIDANDO_SELECAO_FGTS;
- TRATANDO_CONSIGNADO;
- DEFININDO_VENCIMENTO_TAG;
- VALIDANDO_RESUMO;
- AGUARDANDO_CONFIRMACAO_EMISSAO;
- EMITINDO;
- AGUARDANDO_PROCESSAMENTO;
- VALIDANDO_GUIA_GERADA;
- OBTENDO_GUIA;
- OBTENDO_DETALHAMENTOS;
- CONCLUIDO;
- PAUSADO;
- ERRO_CONTROLADO;
- CANCELADO;
- PROCESSADO_MANUALMENTE.

Os nomes são internos e não pressupõem textos ou botões reais do portal.

## 10. Pausar, retomar, parar, próxima CNO e reprocessar

A interface rodará separada da thread de automação.

### PAUSAR

Sinal cooperativo verificado:

- antes de cada ação;
- depois de cada ação;
- durante esperas longas em pequenos intervalos;
- antes de qualquer operação irreversível.

Uma ação já enviada ao navegador não pode ser desfeita magicamente; por isso o fluxo será composto por passos curtos e verificáveis.

### RETOMAR

Após intervenção manual, a automação não continuará cegamente. Antes de retomar deverá executar uma **reconciliação de estado**:

- página/etapa atual;
- CNO atual;
- competência;
- seleção existente;
- vencimento/TAG quando aplicável;
- presença de modal/erro/autenticação.

Se não conseguir provar que o estado atual é compatível, permanecerá pausada/erro controlado.

### PARAR/ENCERRAR

Finaliza em ponto seguro, grava checkpoint e não inicia nova CNO.

### PRÓXIMA CNO

Não será um simples `continue`. A CNO atual receberá status explícito como `PULADA_PELO_OPERADOR`, com motivo/data. Só então a fila avança.

### REPROCESSAR CNO

Só será permitido após consultar o estado persistido e verificar risco de emissão duplicada. CNO com guia confirmadamente emitida não deverá ser reemitida automaticamente sem decisão explícita do operador.

### PROCESSADA MANUALMENTE

Status terminal explícito, com data/hora e observação opcional. Essa CNO deixa de entrar na fila automática daquela execução.

## 11. Velocidade e esperas

A estratégia será híbrida:

1. aguardar condição real do portal;
2. quando a condição for satisfeita, aplicar pequena pausa humana configurável;
3. só então executar a próxima ação.

Parâmetros previstos:

- tempo entre ações;
- tempo após pesquisa;
- tempo após avançar/navegação;
- tempo após geração;
- timeout máximo por condição;
- intervalo de verificação durante esperas.

Não haverá sequência de cliques em alta velocidade.

## 12. Política de erro e guardas

Toda etapa crítica terá **pré-condição**, **ação** e **pós-condição**.

Exemplos:

- antes de pesquisar: provar que estamos na tela correta;
- depois de pesquisar: provar que a CNO retornada é exatamente a esperada;
- depois de selecionar: provar quantidade/estado da seleção;
- depois de preencher vencimento: reler o valor do campo;
- antes de emitir: validar CNO, obra, competência, vencimento, TAG e totais disponíveis;
- depois de emitir: provar existência/número/situação da guia antes de marcar como gerada.

Falha em qualquer guarda:

1. interromper ações automáticas;
2. registrar CNO + etapa + mensagem;
3. capturar screenshot local;
4. salvar checkpoint;
5. mostrar erro ao operador;
6. aguardar decisão explícita.

CAPTCHA, MFA, nova autenticação, aviso inesperado ou mudança estrutural entram nessa política de pausa.

## 13. Confirmação antes da emissão

Configuração: `confirmar_antes_de_emitir = habilitado/desabilitado`.

Quando habilitada, a automação para antes da ação definitiva e mostra:

- CNO;
- código/nome da obra;
- competência;
- vencimento;
- quantidade de trabalhadores/débitos selecionados;
- valores/totais que possam ser validados com segurança;
- TAG.

Ações:

- GERAR;
- PAUSAR;
- CANCELAR.

Mesmo com confirmação desabilitada, todas as validações estruturais continuam obrigatórias.

## 14. Consignado — ponto a decidir antes da implementação

A documentação oficial atual do FGTS Digital descreve a Guia Parametrizada em quatro passos, incluindo **Selecionar Débitos Consignados** antes de Definir Vencimento/Emitir Guia. Débitos de consignado vinculados aos trabalhadores com FGTS incluído podem ser recuperados/adicionados à mesma guia.

Portanto, precisamos decidir o objetivo operacional real:

- **Modelo A — guia combinada:** FGTS + consignado da CNO na mesma GFD, quando houver;
- **Modelo B — guias separadas por decisão operacional:** emitir FGTS e consignado separadamente, se o portal permitir e isso for desejado;
- **Modelo C — outra regra específica** a ser descrita.

Não será implementada a premissa de duas guias sem essa confirmação.

Quando não houver consignado, o resultado será `SEM_CONSIGNADO`, nunca erro.

## 15. Registro persistente por CNO

Campos mínimos:

- run_id;
- CNO;
- código da obra;
- nome da obra;
- competência;
- vencimento;
- status FGTS;
- status consignado;
- status detalhamento FGTS;
- status detalhamento consignado, se aplicável;
- número/identificador da guia quando disponível;
- quantidade de trabalhadores/débitos;
- etapa atual;
- status geral;
- erro;
- data/hora início/fim;
- caminho dos arquivos gerados;
- observação de intervenção manual.

A aplicação deverá conseguir reiniciar e reconstruir a posição a partir desses dados.

## 16. Downloads e detalhamentos

A documentação oficial indica que o FGTS Digital disponibiliza detalhamentos/relatórios e, em determinadas telas, opções em PDF e CSV.

Tratamento previsto:

1. só iniciar captura de download depois de identificar o controle real da interface;
2. aguardar evento real de download;
3. verificar que o arquivo foi concluído e possui conteúdo;
4. classificar o tipo de documento;
5. renomear/mover para pasta segura;
6. registrar o caminho no estado da CNO;
7. se a guia for emitida mas o relatório não puder ser obtido, registrar estados diferentes em vez de marcar tudo como concluído.

Estrutura de pastas sugerida, **ainda não definitiva**:

`FGTS_DIGITAL/<AAAA-MM>/<CODIGO - OBRA>/FGTS`, `CONSIGNADO`, `RE`.

A estrutura será confirmada após observarmos os downloads reais e se FGTS/consignado geram um ou dois documentos/guias.

## 17. Modo TESTE obrigatório

Primeiro ensaio operacional:

1. usar planilha modelo com 1 ou mais registros, mas configurar `modo_teste`;
2. validar toda a planilha;
3. calcular competência/vencimento;
4. conectar ao navegador visível já autenticado;
5. processar somente a primeira CNO selecionada para teste;
6. navegar passo a passo com pausas ampliadas;
7. parar obrigatoriamente antes da emissão definitiva;
8. mostrar resumo de pré-emissão;
9. operador compara visualmente;
10. somente com comando explícito poderá emitir a guia de teste;
11. validar guia e downloads;
12. encerrar o teste sem iniciar a próxima CNO;
13. revisar logs, screenshots e estado persistido antes de habilitar lote.

## 18. Critério para iniciar código de portal

Somente após aprovação desta arquitetura e coleta mínima das evidências listadas em `docs/INFORMACOES_NECESSARIAS.md`.

Até lá, não serão criados seletores, URLs internas, automações de clique ou suposições de interface.
