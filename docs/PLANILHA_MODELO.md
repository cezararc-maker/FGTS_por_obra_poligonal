# Planilha modelo — análise estrutural e decisões confirmadas

Arquivo analisado inicialmente no chat: `FGTS_Extrator_Poligonal.xlsx`.

> O arquivo operacional não deve ser versionado neste repositório público. Este documento registra somente a estrutura necessária para o desenvolvimento.

## Estrutura observada na primeira versão recebida

- Aba: `fgts_servicos (1)`
- Competência: célula `B1`, exibida como `08/2026`
- Vencimento: célula `E1`, exibida na primeira versão como `18/09/206`
- Linha de cabeçalho: linha 3
- Dados: linhas 4 a 29
- Quantidade de registros: 26

Colunas observadas na primeira versão:

| Coluna | Cabeçalho | Uso |
|---|---|---|
| A | Codigo | código interno da obra/serviço |
| B | Servico | descrição do serviço/obra |
| C | TAG | valor literal a ser informado no campo TAG do FGTS Digital |
| D | Documento | número da inscrição a pesquisar no portal |
| E | FGTS | valor apenas para análise/referência |
| F | FGTS Aprendiz | valor apenas para análise/referência |

Na primeira versão recebida foram observados 26 registros, sem duplicidade de código, documento ou TAG e sem campos vazios nas colunas utilizadas.

## Decisões confirmadas pelo usuário

### Tipo de inscrição

O usuário confirmou que criou na planilha atualizada uma coluna específica para indicar o tipo de inscrição.

A automação deverá usar essa coluna diretamente para decidir entre `CNPJ` e `CNO` no portal, sem inferir o tipo a partir do texto de `Servico`.

A versão atualizada da planilha ainda precisa ser validada no chat para registrar o nome exato da coluna e sua posição.

### TAG

A automação deve ler o valor da coluna `TAG` e utilizá-lo literalmente no portal.

Não deve reconstruir a TAG a partir de código e nome da obra. Qualquer futura normalização, truncamento ou remoção de caracteres dependerá de limitação real observada no portal e aprovação do usuário.

### Documento

O documento deve ser tratado como texto para preservar zeros à esquerda, especialmente no CNPJ.

A validação será orientada pelo `Tipo de Inscrição` informado na própria linha.

### FGTS e FGTS Aprendiz

As colunas `FGTS` e `FGTS Aprendiz` são apenas para análise/referência.

O valor efetivamente utilizado para geração e validação operacional da guia será o valor apresentado pelo próprio portal FGTS Digital.

Portanto, divergência entre essas colunas e o portal não deve, por si só, bloquear a automação, salvo decisão futura específica.

### Competência

A competência da planilha deverá ser normalizada para `MM/AAAA` e usada nos campos Inicial e Final do portal.

Para o teste atual: `08/2026`.

### Vencimento

O vencimento será calculado pela automação a partir da competência e das regras aplicáveis.

O vencimento existente na planilha será utilizado somente como conferência visual/adicional. Ele não será a fonte principal da data digitada no portal.

Para a competência `08/2026`, o vencimento esperado é `18/09/2026`.

Se o vencimento calculado pela automação divergir do valor de conferência da planilha, a aplicação deverá informar a divergência ao operador antes do processamento, sem substituir silenciosamente um pelo outro.

## Layout mínimo esperado após atualização

A versão atualizada deverá conter, no mínimo, os seguintes campos funcionais:

```text
Competência
Codigo
Servico
TAG
Tipo Inscrição
Documento
FGTS
FGTS Aprendiz
Vencimento de conferência
```

Os nomes e posições exatos serão registrados depois da validação da planilha atualizada.

## Regras de validação já fechadas

Antes de iniciar o portal, o leitor deverá validar:

- presença do tipo de inscrição;
- tipo limitado inicialmente a `CNPJ` ou `CNO`;
- documento preenchido;
- preservação de zeros à esquerda;
- TAG preenchida;
- código preenchido;
- serviço/obra preenchido;
- competência válida;
- duplicidade de documento;
- duplicidade ou conflito de linhas;
- vencimento calculado e eventual divergência com o vencimento de conferência.

## Pendente apenas de validação da nova planilha

1. Nome exato e posição da nova coluna de tipo de inscrição.
2. Confirmação de que `Documento` está armazenado como texto ou pode ser normalizado sem perda.
3. Confirmação de que o vencimento de conferência foi corrigido para `18/09/2026` no modelo atualizado.
4. Nova contagem de registros e verificação de duplicidades/campos vazios.
