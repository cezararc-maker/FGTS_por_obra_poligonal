# Planilha modelo recebida — análise estrutural

Arquivo analisado no chat: `FGTS_Extrator_Poligonal.xlsx`.

> O arquivo operacional não deve ser versionado neste repositório público. Este documento registra somente a estrutura necessária para o desenvolvimento.

## Estrutura observada

- Aba: `fgts_servicos (1)`
- Competência: célula `B1`, exibida como `08/2026`
- Vencimento: célula `E1`, exibida no arquivo recebido como `18/09/206`
- Linha de cabeçalho: linha 3
- Dados: linhas 4 a 29
- Quantidade de registros: 26

Colunas observadas:

| Coluna | Cabeçalho | Uso proposto |
|---|---|---|
| A | Codigo | código interno da obra/serviço |
| B | Servico | descrição do serviço/obra; no modelo contém também texto `CNPJ:` ou `CNO:` |
| C | TAG | valor literal a ser informado no campo TAG do FGTS Digital |
| D | Documento | número da inscrição a pesquisar no portal |
| E | FGTS | valor de referência ainda a confirmar |
| F | FGTS Aprendiz | valor de referência ainda a confirmar |

## Resultado da validação do modelo recebido

- 26 registros preenchidos;
- 1 registro identificado visualmente como CNPJ;
- 25 registros identificados visualmente como CNO;
- nenhum código duplicado;
- nenhum documento duplicado;
- nenhuma TAG duplicada;
- nenhuma linha de dados com campo vazio nas seis colunas observadas.

## TAG

O modelo recebido resolve a definição da TAG: a automação deve ler o valor da coluna `TAG` e utilizá-lo literalmente no portal, sem montar o texto a partir de Código/Serviço.

Qualquer futura normalização, truncamento ou remoção de caracteres só poderá ser feita se uma limitação real do portal for observada e aprovada pelo usuário.

## Ponto crítico — tipo de inscrição

No modelo atual não existe uma coluna explícita `Tipo de Inscrição`.

O tipo pode ser percebido visualmente no texto da coluna `Servico` (`CNPJ:` ou `CNO:`), mas a arquitetura não deve depender de inferência textual sem decisão explícita.

Recomendação para o layout definitivo: adicionar uma coluna própria, por exemplo:

```text
TIPO INSCRICAO | DOCUMENTO
CNPJ           | 03492162000182
CNO            | 900144852472
```

Valores aceitos inicialmente: `CNPJ` e `CNO`.

Isso permite selecionar diretamente a opção correta no FGTS Digital e validar o tamanho/formato do documento antes de abrir o portal.

## Ponto crítico — CNPJ com zero inicial

O primeiro CNPJ é exibido no Excel como `03492162000182`, mas o valor subjacente foi lido numericamente como `3492162000182`.

Portanto, a automação não pode converter a coluna `Documento` ingenuamente para número/string e confiar no resultado. O zero inicial do CNPJ precisa ser preservado.

Recomendação para o layout definitivo: armazenar `Documento` como texto. Alternativamente, a camada de validação deverá normalizar de acordo com o `Tipo de Inscrição` (14 dígitos para CNPJ e formato validado para CNO), mas a preferência é não depender de formatação visual do Excel.

## Competência

A célula `B1` contém uma data do Excel correspondente a agosto/2026 e é exibida como `08/2026`.

A automação deverá normalizar a competência para `MM/AAAA` e usá-la nos campos Inicial e Final do portal.

## Vencimento

O arquivo recebido exibe em `E1` o texto `18/09/206`, aparentemente faltando um dígito no ano.

Pelo requisito já definido para competência `08/2026`, o vencimento calculado esperado é `18/09/2026`.

A arquitetura mantém como regra principal **calcular o vencimento a partir da competência**. A célula de vencimento da planilha não deve substituir esse cálculo sem decisão posterior; ela poderá, se desejado, ser usada apenas como conferência adicional.

## Valores FGTS e FGTS Aprendiz — decisão pendente

O modelo possui duas colunas monetárias: `FGTS` e `FGTS Aprendiz`.

Antes de implementar qualquer validação de valor no portal, precisamos confirmar qual regra operacional é desejada:

- comparar o `Total FGTS` do portal somente com a coluna `FGTS`;
- comparar com `FGTS + FGTS Aprendiz`;
- tratar os valores separadamente;
- ou utilizar essas colunas apenas como informação, sem bloqueio automático.

Nenhuma dessas hipóteses deve ser codificada sem confirmação do usuário.

## Layout mínimo recomendado para a implementação

Se o usuário aprovar a inclusão explícita do tipo de inscrição, o leitor deverá trabalhar com os campos:

```text
Competência (B1)
Codigo
Servico
TAG
Tipo Inscrição
Documento
FGTS
FGTS Aprendiz
```

A automação também poderá acrescentar os resultados em banco local/relatório separado; não deve sobrescrever silenciosamente os dados originais da planilha.

## Próximas confirmações necessárias

1. Confirmar se será adicionada coluna `Tipo Inscrição` ou se há outra coluna/fonte já prevista para distinguir CNPJ de CNO.
2. Confirmar a regra das colunas `FGTS` e `FGTS Aprendiz` na conferência dos valores do portal.
3. Confirmar se a célula `E1` deve ser apenas informativa/validação ou removida do fluxo, já que o vencimento será calculado pela automação.
4. Corrigir/confirmar o vencimento de teste como `18/09/2026`.
