# FGTS por Obra / Poligonal

Automação assistida em Python para preparação e, futuramente, emissão controlada de Guias Parametrizadas no FGTS Digital por inscrição/obra.

> Estado atual: **Modo TESTE — Fase 1**. Nesta fase o programa **não navega no portal, não clica em Emitir Guia e não baixa documentos**. Ele valida a planilha, calcula/confronta o vencimento, prepara uma única inscrição para teste e comprova a conexão somente leitura com um Chrome visível dedicado.

## Princípios do projeto

- GitHub é a fonte oficial do código e da documentação.
- Navegador sempre visível durante a execução.
- A sessão do FGTS Digital deve estar previamente autenticada pelo usuário.
- O projeto não obtém, armazena ou manipula senhas ou certificados digitais.
- Pausas configuráveis entre etapas.
- Controle de **Pausar**, **Retomar** e **Abortar** nas fases que executarem ações no portal.
- Em erro ou estado inesperado, a execução deve parar com identificação da inscrição, obra e etapa.
- Retomada somente após revalidação do estado da tela; nunca continuar às cegas após intervenção manual.
- Logs estruturados e captura de evidência em falhas.
- Dados reais, PDFs, planilhas operacionais, screenshots com informações sensíveis e logs de execução não devem ser versionados.

## Requisitos da Fase 1

- Windows 10 ou 11;
- Python 3.11;
- Google Chrome;
- Git;
- acesso ao portal FGTS Digital realizado manualmente pelo operador.

## Branch de teste

```text
feat/modo-teste-fase1
```

## 1. Obter o projeto

Se ainda não tiver o repositório no computador:

```powershell
git clone https://github.com/cezararc-maker/FGTS_por_obra_poligonal.git
cd FGTS_por_obra_poligonal
git checkout feat/modo-teste-fase1
```

Se já tiver o repositório:

```powershell
cd CAMINHO\FGTS_por_obra_poligonal
git fetch origin
git checkout feat/modo-teste-fase1
git pull origin feat/modo-teste-fase1
```

## 2. Instalar o ambiente de teste

No Explorer, execute:

```text
scripts\instalar_teste.bat
```

Ele cria `.venv`, atualiza o `pip` e instala o projeto localmente.

## 3. Abrir o Chrome dedicado

Execute:

```text
scripts\abrir_chrome_teste.bat
```

Esse Chrome usa um perfil dedicado em `%LOCALAPPDATA%\FGTS_Poligonal\ChromeProfile` e habilita depuração remota somente para que o Python se conecte à janela visível.

O BAT **não abre uma URL específica e não realiza login**.

No Chrome que abrir:

1. acesse o FGTS Digital manualmente;
2. faça autenticação/certificado manualmente;
3. assuma a procuração/empresa manualmente;
4. deixe o navegador aberto na tela desejada.

## 4. Abrir a aplicação de teste

Execute:

```text
scripts\executar_teste.bat
```

Na interface:

1. clique em `Selecionar Excel`;
2. selecione a planilha atualizada;
3. aguarde a validação;
4. confira competência, vencimento e quantidade de inscrições;
5. escolha uma única inscrição na tabela;
6. clique em `Preparar teste de 1 inscrição`;
7. confira o resumo;
8. com o Chrome dedicado aberto e autenticado, clique em `Testar conexão com Chrome`.

### Resultado esperado com a planilha atual

Para competência `08/2026`:

```text
Vencimento calculado: 18/09/2026
```

A interface deve listar 26 registros válidos, sendo 1 CNPJ e 25 CNOs, desde que a planilha utilizada corresponda ao modelo validado no projeto.

## O que o teste de Chrome faz

A aplicação conecta ao Chrome em:

```text
http://127.0.0.1:9222
```

Ela lê apenas:

- quantidade de páginas abertas;
- título da página atual;
- URL da página atual.

Nesta fase, **nenhum clique é executado pelo programa**.

## Testes automatizados locais

Após instalar o ambiente:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Os testes cobrem inicialmente:

- vencimento de 08/2026 em 18/09/2026;
- antecipação de fim de semana;
- suporte a feriado informado explicitamente;
- normalização de CNPJ com zero inicial;
- formato de CNO com 12 dígitos;
- leitura de uma planilha mínima válida.

## Próxima fase

Somente depois de validar esta Fase 1, a próxima implementação será o **Modo TESTE — Fase 2**:

1. conectar ao Chrome visível;
2. confirmar sessão/página esperada;
3. navegar apenas até `Gestão de Guias > Emissão de Guia Parametrizada` usando seletores observados e testados;
4. preencher uma única competência e uma única inscrição;
5. pesquisar e validar o resultado;
6. parar antes de adicionar/emitir qualquer guia enquanto ajustamos as guardas.

A emissão definitiva continuará bloqueada até validação explícita do usuário.

## Segurança

O repositório é público. Não versionar:

- planilhas reais;
- PDFs de guias;
- CPF/CNPJ/CNO operacionais em exemplos;
- screenshots com dados pessoais;
- cookies/tokens;
- certificado digital;
- arquivos PFX/P12;
- credenciais.
