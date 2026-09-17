# Planilha modelo — análise estrutural e decisões confirmadas

Arquivo atualizado analisado no chat: `FGTS_Extrator_Poligonal(2).xlsx`.

> O arquivo operacional não deve ser versionado neste repositório público. Este documento registra somente a estrutura necessária para o desenvolvimento.

## Estrutura validada na versão atualizada

- Aba: `fgts_servicos (1)`
- Competência: célula `B1`, armazenada como data de agosto/2026 e exibida como `08/2026`
- Vencimento de conferência: célula `E1`, armazenada como `18/09/2026`
- Linha de cabeçalho: linha 3
- Dados: linhas 4 a 29
- Quantidade de registros: 26

Colunas atuais:

| Coluna | Cabeçalho | Uso |
|---|---|---|
| A | Codigo | código interno da obra/serviço |
| B | Tipo Inscrição | determina diretamente `CNPJ` ou `CNO` no portal |
| C | Servico | descrição do serviço/obra |
| D | TAG | valor a ser informado no campo TAG do FGTS Digital |
| E | Inscrição | número da inscrição (CNPJ ou CNO) a pesquisar no portal |
| F | FGTS | valor apenas para análise/referência |
| G | FGTS Aprendiz | valor apenas para análise/referência |

## Validação do conteúdo atualizado

- 26 registros preenchidos;
- 1 linha com tipo `CNPJ`;
- 25 linhas com tipo `CNO`;
- nenhuma duplicidade de código;
- nenhuma duplicidade de inscrição;
- nenhuma duplicidade de TAG;
- nenhuma linha de dados com campos funcionais vazios;
- vencimento de conferência correto em `18/09/2026`.

## Tipo de inscrição e número da inscrição

A decisão está fechada:

- a coluna `Tipo Inscrição` informa qual opção deverá ser usada no portal (`CNPJ` ou `CNO`);
- a coluna `Inscrição` contém o número correspondente que será informado na pesquisa.

A automação não deve inferir o tipo a partir do texto de `Servico`.

Valores aceitos inicialmente para `Tipo Inscrição`: `CNPJ` e `CNO`.

## TAG

A automação deve ler o valor resultante da coluna `TAG` e utilizá-lo no portal.

Qualquer futura normalização, truncamento ou remoção de caracteres dependerá de limitação real observada no portal e aprovação do usuário.

## Inscrição e zeros à esquerda

Na versão atualizada, a coluna `Inscrição` continua armazenada como valor numérico. Existe um CNPJ que visualmente começa com zero, mas a leitura bruta do valor numérico perde esse zero inicial.

Isso não impede o desenvolvimento, porque o leitor terá o `Tipo Inscrição` explícito e poderá normalizar a inscrição antes do uso:

- `CNPJ`: converter para somente dígitos e completar à esquerda até 14 dígitos;
- `CNO`: tratar como identificador textual e validar conforme o formato adotado no projeto.

Mesmo assim, quando possível, é preferível manter a coluna `Inscrição` como texto no Excel para preservar o identificador exatamente como digitado.

A automação nunca deve enviar ao portal uma inscrição sem validar o número de dígitos e o tipo informado.

## FGTS e FGTS Aprendiz

As colunas `FGTS` e `FGTS Aprendiz` são apenas para análise/referência.

O valor efetivamente utilizado para geração e validação operacional da guia será o valor apresentado pelo próprio portal FGTS Digital.

Divergência entre essas colunas e o portal não deve bloquear a automação, salvo decisão futura específica.

## Competência

A competência da planilha deverá ser normalizada para `MM/AAAA` e usada nos campos Inicial e Final do portal.

Para o teste atual: `08/2026`.

## Vencimento

O vencimento será calculado pela automação a partir da competência e das regras aplicáveis.

O vencimento existente na planilha será utilizado somente como conferência visual/adicional. Ele não será a fonte principal da data digitada no portal.

Para a competência `08/2026`, o vencimento esperado e também presente no modelo atualizado é `18/09/2026`.

Se o vencimento calculado pela automação divergir do valor de conferência da planilha, a aplicação deverá informar a divergência ao operador antes do processamento, sem substituir silenciosamente um pelo outro.

## Layout funcional fechado para o leitor

O leitor deverá trabalhar com:

```text
Competência (B1)
Vencimento de conferência (E1)
Codigo
Tipo Inscrição
Servico
TAG
Inscrição
FGTS
FGTS Aprendiz
```

A planilha original não deve ser sobrescrita silenciosamente. Estados da execução, logs e resultados deverão ficar em armazenamento próprio da aplicação e/ou relatório separado.

## Regras de validação antes de abrir o portal

- planilha e aba esperada acessíveis;
- competência válida;
- vencimento de conferência legível;
- código preenchido;
- `Tipo Inscrição` preenchido e limitado inicialmente a `CNPJ`/`CNO`;
- serviço preenchido;
- TAG preenchida;
- inscrição preenchida;
- inscrição normalizada de acordo com o tipo;
- CNPJ preservado/normalizado para 14 dígitos, inclusive quando inicia por zero;
- duplicidade de inscrição;
- duplicidade ou conflito de linhas;
- vencimento calculado e eventual divergência com o vencimento de conferência.

## Situação da planilha

Com a versão atualizada, a estrutura da planilha está aprovada para seguirmos para a implementação do leitor e das regras de negócio, após a aprovação geral da arquitetura pelo usuário.
