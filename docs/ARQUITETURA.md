# Arquitetura inicial

## 1. Objetivo

Construir uma automação assistida para emissão de guias individualizadas do FGTS Digital por CNO/obra, mantendo o operador no controle da execução e utilizando uma sessão do navegador previamente autenticada.

A automação não deve funcionar como um robô cego. Toda ação no portal deve ocorrer dentro de uma máquina de estados conhecida, com validações antes e depois das ações relevantes.

## 2. Tecnologia proposta

### Python

Python será a linguagem principal do projeto.

### Navegador: Playwright conectado a navegador Chromium visível

Proposta inicial: utilizar **Playwright para Python**, conectado via CDP a uma instância visível do Chrome/Chromium iniciada para a automação.

Motivos:

- permite navegador visível;
- possui mecanismos robustos de espera e inspeção do DOM;
- possibilita validar conteúdo antes e depois de cada ação;
- facilita download controlado e captura de screenshot em falhas;
- pode se conectar a uma sessão de navegador já aberta **desde que essa instância tenha sido iniciada com depuração remota habilitada**.

Importante: não será assumido que uma janela comum do Chrome, aberta sem depuração remota, possa ser anexada posteriormente de forma confiável. O desenho preferencial é:

1. iniciar uma instância dedicada e visível do navegador com um perfil próprio para a automação;
2. o usuário realiza login, seleção de certificado e procuração manualmente;
3. somente depois o Python se conecta à sessão autenticada;
4. o Python nunca recebe senha nem dados do certificado.

A escolha definitiva entre Chrome/Edge e a forma de conexão será confirmada com o ambiente real do usuário antes da implementação.

## 3. Componentes previstos

```text
src/
  fgts_obra/
    app.py                  # entrada da aplicação
    config.py               # parâmetros locais e defaults seguros
    models.py               # CNO, obra, competência, execução
    excel_reader.py         # leitura e validação da planilha
    calendar_rules.py       # competência e vencimento
    control_panel.py        # Pausar / Retomar / Abortar
    execution_state.py      # máquina de estados e checkpoints
    logging_setup.py        # logs estruturados
    browser/
      connection.py         # conexão à sessão visível
      guards.py             # validações antes/depois das ações
      fgts_portal.py        # fluxo do portal (somente após levantamento)
      selectors.py          # seletores confirmados, nunca inferidos
    workflows/
      generate_guide.py     # orquestração por CNO/obra

tests/
  test_calendar_rules.py
  test_excel_reader.py
  test_tag_format.py
  test_execution_state.py

docs/
  ARQUITETURA.md
  INFORMACOES_NECESSARIAS.md
```

Os nomes podem ser ajustados durante a implementação, mas as responsabilidades devem permanecer separadas.

## 4. Modelo de execução

### Fase A — preparação

1. carregar configuração;
2. solicitar competência;
3. mostrar confirmação:
   - Competência a processar;
   - Período inicial;
   - Período final;
4. só continuar após confirmação manual;
5. carregar e validar Excel;
6. calcular vencimento;
7. conectar à sessão autenticada do navegador;
8. tentar identificar a empresa visível no portal, quando houver um elemento confiável para isso;
9. mostrar resumo final:
   - competência;
   - vencimento calculado;
   - quantidade de CNOs válidos;
   - empresa encontrada quando possível;
10. aguardar clique em SIM.

Nenhuma CNO é processada antes das duas confirmações.

### Fase B — processamento de cada CNO

Cada obra será processada isoladamente. O estado mínimo registrado deverá conter:

- índice atual;
- CNO;
- código da obra;
- nome da obra;
- competência;
- etapa atual;
- data/hora;
- resultado da última validação;
- status: aguardando / executando / pausado / concluído / erro / abortado.

O fluxo específico do portal só será implementado após confirmar elementos reais da interface.

## 5. Máquina de estados

Estados funcionais sugeridos:

```text
PREPARANDO
AGUARDANDO_CONFIRMACAO_COMPETENCIA
CARREGANDO_PLANILHA
VALIDANDO_PLANILHA
CONECTANDO_NAVEGADOR
AGUARDANDO_CONFIRMACAO_RESUMO

CNO_INICIANDO
CNO_ACESSANDO_GUIA_PARAMETRIZADA
CNO_CONFIGURANDO_FILTROS
CNO_PESQUISANDO
CNO_VALIDANDO_RESULTADO
CNO_SELECIONANDO_DEBITOS
CNO_AVANCANDO
CNO_DEFININDO_VENCIMENTO_TAG
CNO_VALIDANDO_VENCIMENTO_TAG
CNO_EMITINDO_GUIA
CNO_VALIDANDO_EMISSAO
CNO_FINALIZADO

PAUSADO
ERRO_CONTROLADO
ABORTADO
FINALIZADO
```

Os nomes das etapas do portal são conceituais neste momento e **não implicam seletores ou comportamento técnico já conhecidos**.

## 6. Pausar, retomar e abortar

Será utilizado um painel de controle local, preferencialmente em Tkinter, com pelo menos:

- `PAUSAR`;
- `RETOMAR`;
- `ABORTAR`;
- exibição de CNO/obra/etapa atual;
- última mensagem de status.

A pausa será cooperativa e de alta frequência: todas as ações do navegador passarão por um wrapper que verifica os sinais de pausa/aborto antes e depois de ações e durante esperas longas em intervalos curtos.

Limitação técnica importante: uma chamada já entregue ao navegador não pode ser magicamente desfeita no meio. Por isso, o projeto evitará operações longas monolíticas e usará esperas curtas e verificáveis.

Ao retomar após intervenção manual, o sistema **não continua simplesmente da próxima linha de código**. Primeiro executa uma validação do estado atual da página. Se a página não estiver no estado esperado, entra em `ERRO_CONTROLADO` e pede nova intervenção.

## 7. Pausas configuráveis

Configurações previstas, sem hardcode no fluxo:

```toml
[delays]
before_action = 0.8
after_action = 1.2
after_search = 2.0
after_navigation = 2.0
```

Os valores acima são apenas exemplos de estrutura e não serão adotados como defaults definitivos antes do teste assistido.

## 8. Validações obrigatórias

Antes de qualquer ação irreversível, deverá existir uma condição verificável.

Exemplos conceituais:

- confirmar que a tela atual é a tela esperada;
- confirmar que a competência exibida é a competência solicitada;
- confirmar que o CNO encontrado é exatamente o CNO da planilha;
- confirmar a quantidade/estado dos débitos selecionados;
- confirmar que TAG foi preenchida com o valor esperado;
- confirmar que vencimento exibido é exatamente o calculado;
- confirmar que a emissão foi concluída antes de marcar a obra como finalizada.

Se qualquer validação falhar, nenhuma etapa seguinte é executada automaticamente.

## 9. Logs e evidências

Cada execução deverá gerar logs estruturados localmente, sem versionamento no GitHub.

Campos mínimos:

- `run_id`;
- timestamp;
- competência;
- CNO;
- código da obra;
- nome da obra;
- etapa;
- ação;
- resultado;
- mensagem;
- exceção, quando houver.

Em falha:

1. pausar o fluxo;
2. registrar etapa e CNO;
3. capturar screenshot local;
4. preservar checkpoint;
5. mostrar mensagem clara ao operador.

## 10. Checkpoint e recuperação

Será mantido um checkpoint local por execução. O objetivo é permitir identificar com precisão:

- quais CNOs concluíram;
- qual CNO estava sendo processado;
- em qual etapa parou;
- se a retomada automática é segura ou se exige revalidação/manual.

Por segurança, uma nova execução não deverá presumir que uma guia foi emitida apenas porque a etapa anterior foi iniciada. A conclusão só será registrada após validação positiva da emissão.

## 11. Leitura do Excel

A planilha será lida com `openpyxl` ou `pandas` + `openpyxl`, mantendo CNO como texto para evitar perda de zeros e alterações de formatação.

Validações previstas:

- CNO vazio;
- CNO duplicado;
- código de obra vazio;
- nome de obra vazio;
- linhas inteiramente vazias;
- CNO com formato inesperado;
- conflito entre obras duplicadas.

A aba, linha de cabeçalho e nomes exatos das colunas ainda precisam ser confirmados.

## 12. Competência e vencimento

Para débitos mensais, a regra base confirmada é:

- vencimento no dia 20 do mês subsequente à competência;
- se o dia 20 não for útil, antecipar para o dia útil imediatamente anterior.

Para `08/2026`:

- data-base: `20/09/2026`;
- domingo;
- vencimento esperado: `18/09/2026`.

A implementação deverá considerar calendário de dias não úteis aplicável ao recolhimento do FGTS. A fonte/calendário utilizada será explicitamente documentada e testada.

O projeto não deve aplicar a regra mensal indiscriminadamente a débitos rescisórios ou situações especiais; esses casos exigem regra própria.

## 13. TAG

A função de TAG será isolada e testável:

```text
format_tag(codigo_obra, nome_obra) -> str
```

Nenhum padrão será implementado até o usuário informar:

- ordem dos campos;
- separador;
- espaços;
- caixa alta/baixa;
- limite de caracteres;
- tratamento quando o nome ultrapassar o limite;
- caracteres que devem ser removidos ou preservados.

## 14. Segurança de dados

O repositório é público neste momento. Portanto:

- não versionar planilha real;
- não versionar CNOs reais;
- não versionar CNPJ/CPF reais;
- não versionar screenshots do portal com dados identificáveis;
- não versionar cookies, perfis do navegador, certificados, arquivos `.pfx/.p12`, tokens ou segredos;
- não versionar PDFs das guias reais.

Caso seja necessário guardar exemplos no repositório, eles deverão ser totalmente fictícios.

## 15. Critério para começar a automação do portal

O módulo `browser/fgts_portal.py` só deverá ser implementado depois de obter evidência suficiente para cada etapa: tela, elemento-alvo, estado esperado antes da ação e estado verificável depois da ação.
