# FGTS por Obra / Poligonal

Automação assistida em Python para preparação e emissão controlada de Guias Parametrizadas no FGTS Digital por inscrição/obra.

> Estado atual: **Modo TESTE — Fase 2**. Nesta fase o programa pode navegar até `Gestão de Guias > Emissão de Guia Parametrizada`, preencher competência e filtros, pesquisar **uma única inscrição** e parar no resultado. Ele **não seleciona débitos, não clica em Adicionar à guia, não avança para consignado e não emite guia**.

## Princípios do projeto

- GitHub é a fonte oficial do código e da documentação.
- Navegador sempre visível durante a execução.
- A sessão do FGTS Digital deve estar previamente autenticada pelo usuário.
- O projeto não obtém, armazena ou manipula senhas ou certificados digitais.
- Em estado inesperado, a execução para em vez de clicar por aproximação.
- Dados reais, PDFs, planilhas operacionais, screenshots e logs locais não são versionados.

## Requisitos

- Windows 10 ou 11;
- Python 3.11;
- Google Chrome;
- Git;
- acesso ao FGTS Digital realizado manualmente pelo operador.

## Branch da Fase 2

```text
feat/modo-teste-fase2
```

Se o repositório já está no computador:

```powershell
cd "C:\Users\Cezar.CONTALEX\Desktop\GitHub\FGTS_por_obra_poligonal"
git fetch origin
git checkout feat/modo-teste-fase2
git pull origin feat/modo-teste-fase2
```

O ambiente `.venv` criado na Fase 1 pode ser reutilizado. Se necessário, execute novamente:

```powershell
.\scripts\instalar_teste.bat
```

## Abrir o Chrome dedicado

Execute em um PowerShell separado:

```powershell
cd "C:\Users\Cezar.CONTALEX\Desktop\GitHub\FGTS_por_obra_poligonal"
.\scripts\abrir_chrome_teste.bat
```

No Chrome que abrir:

1. acesse o FGTS Digital manualmente;
2. faça autenticação/certificado manualmente;
3. assuma a procuração/empresa manualmente;
4. deixe a sessão aberta.

## Abrir a aplicação

Em outro PowerShell:

```powershell
cd "C:\Users\Cezar.CONTALEX\Desktop\GitHub\FGTS_por_obra_poligonal"
.\scripts\executar_teste.bat
```

Na aplicação:

1. selecione a planilha;
2. confirme competência, vencimento e os 26 registros;
3. escolha **uma única inscrição**;
4. opcionalmente clique em `Preparar 1 inscrição` para revisar os dados;
5. clique em `FASE 2 — Pesquisar inscrição`;
6. leia a confirmação e só prossiga se a inscrição selecionada estiver correta;
7. acompanhe o Chrome visível e o log.

## O que a Fase 2 pode fazer

A execução autorizada nesta fase é limitada a:

1. validar que a página ativa pertence ao FGTS Digital;
2. abrir `Gestão de Guias`;
3. abrir `Emissão de Guia Parametrizada`;
4. confirmar a etapa `Selecionar Débitos FGTS`;
5. preencher `Inicial` e `Final` com a competência da planilha;
6. conferir e desmarcar `Vencido`;
7. abrir `Pesquisa Expandida`;
8. trabalhar somente no contexto `Estabelecimento da Remuneração`;
9. selecionar `CNPJ` ou `CNO` conforme a planilha;
10. preencher a inscrição;
11. clicar em `Pesquisar`;
12. localizar a tabela de resultado e confirmar a inscrição;
13. **parar imediatamente**.

## Bloqueios obrigatórios da Fase 2

Não existe código nesta fase para:

- selecionar o checkbox dos débitos;
- `Adicionar à guia`;
- `Avançar`;
- tratar consignado;
- definir vencimento/TAG no portal;
- `Emitir Guia`;
- baixar PDF/CSV.

## Comportamento em erro

Se um elemento não puder ser identificado de forma única ou a página não atingir a pós-condição esperada, a automação para.

Quando possível, uma captura local é salva em:

```text
screenshots\fase2_erro_AAAAMMDD_HHMMSS.png
```

A pasta `screenshots` está no `.gitignore` e não é enviada ao repositório.

## Seletores da interface do portal

A implementação usa como base os nomes acessíveis observados no mapeamento manual, entre eles:

- `Gestão de Guias`;
- `Emissão de Guia Parametrizada`;
- `Selecionar Débitos FGTS`;
- `Inicial`;
- `Final`;
- `Vencido`;
- `Expandir Pesquisa`;
- `Ocultar Pesquisa Expandida`;
- `Estabelecimento da Remuneração`;
- `CNPJ` / `CNO`;
- `Pesquisar`.

Esses seletores ainda estão sendo **validados por código no portal real**. Se algum deles divergir da estrutura atual, o teste deve parar e o seletor será ajustado com base no erro observado — não por adivinhação.

## Testes automatizados locais

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Os testes locais existentes cobrem as regras de planilha, normalização de inscrições e vencimento. O fluxo do portal depende do teste controlado no ambiente real.

## Segurança

O repositório é público. Não versionar planilhas reais, PDFs de guias, inscrições operacionais, screenshots com dados pessoais, cookies/tokens, certificado digital, arquivos PFX/P12 ou credenciais.
