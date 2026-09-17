from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from playwright.sync_api import Locator, Page


class PortalFlowError(RuntimeError):
    """Erro controlado: a automação não conseguiu provar o próximo estado."""


@dataclass
class ResultadoPesquisaPortal:
    tipo_inscricao: str
    inscricao: str
    competencia: str
    linhas_resultado: int
    inscricao_encontrada_na_tabela: bool


LogFn = Callable[[str], None]


def _digitos(texto: str) -> str:
    return re.sub(r"\D", "", texto or "")


def _visiveis(locator: Locator) -> list[Locator]:
    encontrados: list[Locator] = []
    for i in range(locator.count()):
        item = locator.nth(i)
        try:
            if item.is_visible():
                encontrados.append(item)
        except Exception:
            continue
    return encontrados


def _unico_visivel(locator: Locator, descricao: str) -> Locator:
    itens = _visiveis(locator)
    if len(itens) != 1:
        raise PortalFlowError(
            f"Esperado exatamente 1 elemento visível para '{descricao}', mas foram encontrados {len(itens)}."
        )
    return itens[0]


def _clicar_texto_priorizado(page: Page, texto: str) -> None:
    tentativas = (
        page.get_by_role("link", name=texto, exact=True),
        page.get_by_role("button", name=texto, exact=True),
        page.get_by_text(texto, exact=True),
    )
    for locator in tentativas:
        itens = _visiveis(locator)
        if len(itens) == 1:
            itens[0].click()
            return
        if len(itens) > 1:
            raise PortalFlowError(f"Mais de um elemento visível encontrado para '{texto}'.")
    raise PortalFlowError(f"Elemento visível não encontrado: '{texto}'.")


def _campo_competencia(page: Page, nome: str) -> Locator:
    candidatos = page.get_by_role("combobox", name=nome, exact=True)
    itens = _visiveis(candidatos)
    if len(itens) != 1:
        candidatos = page.get_by_label(nome, exact=True)
        itens = _visiveis(candidatos)
    if len(itens) != 1:
        raise PortalFlowError(f"Campo de competência '{nome}' não foi identificado de forma única.")
    return itens[0]


def _texto_competencia_renderizado(campo: Locator, valor_esperado: str) -> str:
    candidatos: list[str] = []
    try:
        valor_input = campo.input_value().strip()
        if valor_input:
            candidatos.append(valor_input)
    except Exception:
        pass

    atual = campo
    for _ in range(4):
        try:
            atual = atual.locator("xpath=..")
            if atual.count() != 1:
                break
            texto = " ".join(atual.inner_text().split())
            if texto:
                candidatos.append(texto)
            if valor_esperado in texto:
                return valor_esperado
        except Exception:
            break

    for texto in candidatos:
        achado = re.search(r"\b(0[1-9]|1[0-2])/\d{4}\b", texto)
        if achado:
            return achado.group(0)
    return candidatos[0] if candidatos else ""


def _opcao_competencia_visivel(page: Page, valor: str) -> Locator:
    opcoes = _visiveis(page.get_by_role("option", name=valor, exact=True))
    if len(opcoes) == 1:
        return opcoes[0]
    if len(opcoes) > 1:
        raise PortalFlowError(f"A lista apresentou mais de uma opção visível para '{valor}'.")

    textos = _visiveis(page.get_by_text(valor, exact=True))
    candidatos: list[Locator] = []
    for item in textos:
        try:
            popup = item.locator(
                "xpath=ancestor::*[@role='listbox' or @role='menu' or "
                "contains(@class,'dropdown') or contains(@class,'overlay') or "
                "contains(@class,'panel')][1]"
            )
            if popup.count() == 1 and popup.is_visible():
                candidatos.append(item)
        except Exception:
            continue

    if len(candidatos) == 1:
        return candidatos[0]
    if len(candidatos) > 1:
        raise PortalFlowError(f"A lista apresentou mais de uma opção candidata para '{valor}'.")
    raise PortalFlowError(f"A competência '{valor}' não apareceu na lista de competências em aberto.")


def _selecionar_competencia(page: Page, nome: str, valor: str) -> None:
    campo = _campo_competencia(page, nome)
    campo.click()
    page.wait_for_timeout(300)
    opcao = _opcao_competencia_visivel(page, valor)
    opcao.click()
    page.wait_for_timeout(350)

    recebido = _texto_competencia_renderizado(campo, valor).strip()
    if recebido != valor:
        raise PortalFlowError(
            f"Competência {nome} divergente após seleção: esperado '{valor}', recebido '{recebido}'."
        )


def _desmarcar_vencido(page: Page) -> None:
    candidatos = page.get_by_role("checkbox", name="Vencido", exact=True)
    itens = _visiveis(candidatos)
    if len(itens) != 1:
        candidatos = page.get_by_label("Vencido", exact=True)
        itens = _visiveis(candidatos)
    if len(itens) != 1:
        raise PortalFlowError("Controle 'Vencido' não foi identificado de forma única.")

    controle = itens[0]
    if not controle.is_checked():
        return

    controle_id = controle.get_attribute("id")
    if controle_id:
        labels = _visiveis(page.locator(f'label[for="{controle_id}"]'))
        if len(labels) == 1:
            labels[0].click()
        elif len(labels) > 1:
            raise PortalFlowError("Mais de um label visível foi encontrado para 'Vencido'.")
        else:
            _unico_visivel(page.get_by_text("Vencido", exact=True), "label Vencido").click()
    else:
        _unico_visivel(page.get_by_text("Vencido", exact=True), "label Vencido").click()

    page.wait_for_timeout(250)
    if controle.is_checked():
        raise PortalFlowError("O controle 'Vencido' permaneceu marcado após o clique.")


def _expandir_pesquisa(page: Page) -> None:
    expandir = _visiveis(page.get_by_role("button", name="Expandir Pesquisa", exact=True))
    if len(expandir) == 1:
        expandir[0].click()
        page.wait_for_timeout(350)
        return

    # Se os campos expandidos já estiverem visíveis, consideramos a seção aberta.
    if _visiveis(page.get_by_text("Estabelecimento da Remuneração", exact=True)):
        return

    ocultar = _visiveis(page.get_by_role("button", name="Ocultar Pesquisa Expandida", exact=True))
    if len(ocultar) == 1:
        return
    raise PortalFlowError("Não foi possível determinar se a Pesquisa Expandida está aberta ou fechada.")


def _secao_estabelecimento(page: Page) -> Locator:
    """Retorna somente o bloco 'Estabelecimento da Remuneração'.

    A tela possui outros blocos com CNPJ/CNO (Tomador e Local de Trabalho), então
    qualquer ancestral que também contenha esses títulos é rejeitado.
    """
    titulo = _unico_visivel(
        page.get_by_text("Estabelecimento da Remuneração", exact=True),
        "Estabelecimento da Remuneração",
    )

    candidatos: list[tuple[int, Locator]] = []
    atual = titulo
    for _ in range(7):
        atual = atual.locator("xpath=..")
        if atual.count() != 1:
            break
        try:
            if not atual.is_visible():
                continue
            texto = " ".join(atual.inner_text().split())
        except Exception:
            continue

        if "Estabelecimento da Remuneração" not in texto:
            continue
        if "CNPJ" not in texto or "CNO" not in texto:
            continue
        if "Tomador de Serviços" in texto or "Local de Trabalho Atual" in texto:
            continue

        campos = _visiveis(
            atual.locator(
                "input:enabled:not([type='radio']):not([type='checkbox']):"
                "not([type='hidden']):not([type='button']):not([type='submit'])"
            )
        )
        # O bloco esperado contém o campo 'Informe CNPJ, CAEPF ou CNO'.
        if campos:
            candidatos.append((len(texto), atual))

    if not candidatos:
        raise PortalFlowError(
            "O bloco 'Estabelecimento da Remuneração' não pôde ser delimitado sem misturar "
            "Tomador de Serviços ou Local de Trabalho Atual."
        )

    candidatos.sort(key=lambda item: item[0])
    return candidatos[0][1]


def _selecionar_tipo_e_campo(secao: Locator, tipo: str) -> Locator:
    # Dentro do bloco já delimitado deve existir apenas um CNPJ/CNO correspondente.
    tipo_texto = _unico_visivel(secao.get_by_text(tipo, exact=True), f"tipo de inscrição {tipo}")
    tipo_texto.click()

    # O campo do Estabelecimento da Remuneração possui placeholder próprio observado na tela.
    campos_placeholder = _visiveis(
        secao.locator("input[placeholder*='CNPJ'][placeholder*='CAEPF'][placeholder*='CNO']")
    )
    if len(campos_placeholder) == 1:
        return campos_placeholder[0]
    if len(campos_placeholder) > 1:
        raise PortalFlowError(
            "Mais de um campo de inscrição foi encontrado dentro de 'Estabelecimento da Remuneração'."
        )

    # Fallback ainda restrito ao bloco correto.
    campos = _visiveis(
        secao.locator(
            "input:enabled:not([type='radio']):not([type='checkbox']):not([type='hidden']):"
            "not([type='button']):not([type='submit'])"
        )
    )
    if len(campos) == 1:
        return campos[0]

    raise PortalFlowError(
        "O campo de inscrição do bloco 'Estabelecimento da Remuneração' não foi identificado de forma única."
    )


def _localizar_tabela_resultado(page: Page) -> Locator | None:
    for i in range(page.locator("table").count()):
        tabela = page.locator("table").nth(i)
        try:
            if not tabela.is_visible():
                continue
            texto = tabela.inner_text()
        except Exception:
            continue
        if "Competência de Apuração" in texto and "Estabelecimento da Remuneração" in texto:
            return tabela
    return None


def executar_pesquisa_segura(
    page: Page,
    *,
    tipo_inscricao: str,
    inscricao: str,
    competencia: str,
    log: LogFn,
) -> ResultadoPesquisaPortal:
    """Fase 2: pesquisa uma inscrição e PARA no resultado.

    Proibido nesta função: selecionar débitos, Adicionar à guia, Avançar ou Emitir Guia.
    """
    if tipo_inscricao not in {"CNPJ", "CNO"}:
        raise PortalFlowError(f"Tipo de inscrição não suportado: {tipo_inscricao!r}.")

    if "fgtsdigital.sistema.gov.br" not in page.url.lower():
        raise PortalFlowError(
            "A página ativa não pertence ao FGTS Digital. Abra a tela inicial do portal no Chrome dedicado."
        )

    log("[1/8] Sessão FGTS Digital confirmada.")

    if not _visiveis(page.get_by_text("Selecionar Débitos FGTS", exact=False)):
        log("[2/8] Abrindo Gestão de Guias...")
        _clicar_texto_priorizado(page, "Gestão de Guias")
        page.wait_for_timeout(400)
        log("[3/8] Abrindo Emissão de Guia Parametrizada...")
        _clicar_texto_priorizado(page, "Emissão de Guia Parametrizada")
        page.get_by_text("Selecionar Débitos FGTS", exact=False).first.wait_for(
            state="visible", timeout=15_000
        )
    else:
        log("[2/8] A tela de Guia Parametrizada já está aberta.")

    log(f"[4/8] Selecionando competência Inicial/Final na lista: {competencia}...")
    _selecionar_competencia(page, "Inicial", competencia)
    _selecionar_competencia(page, "Final", competencia)

    log("[5/8] Conferindo filtro Vencido...")
    _desmarcar_vencido(page)

    log("[6/8] Abrindo Pesquisa Expandida...")
    _expandir_pesquisa(page)
    secao = _secao_estabelecimento(page)

    log(f"[7/8] Selecionando {tipo_inscricao} em Estabelecimento da Remuneração e preenchendo a inscrição...")
    campo = _selecionar_tipo_e_campo(secao, tipo_inscricao)
    campo.fill(inscricao)
    campo.press("Tab")
    page.wait_for_timeout(250)
    recebido = _digitos(campo.input_value())
    if recebido != _digitos(inscricao):
        raise PortalFlowError(
            f"Inscrição divergente após preenchimento: esperado {inscricao}, recebido {campo.input_value()!r}."
        )

    log("[8/8] Executando somente a pesquisa. A automação irá parar no resultado...")
    pesquisar = _unico_visivel(page.get_by_role("button", name="Pesquisar", exact=True), "Pesquisar")
    pesquisar.click()

    tabela: Locator | None = None
    limite = time.monotonic() + 20
    while time.monotonic() < limite:
        tabela = _localizar_tabela_resultado(page)
        if tabela is not None:
            break
        page.wait_for_timeout(300)

    if tabela is None:
        raise PortalFlowError(
            "A pesquisa foi enviada, mas a tabela de resultados não apareceu em até 20 segundos. "
            "A automação parou sem selecionar ou adicionar qualquer débito."
        )

    linhas = tabela.locator("tbody tr")
    qtd_linhas = sum(1 for i in range(linhas.count()) if linhas.nth(i).is_visible())
    texto_tabela = tabela.inner_text()
    encontrada = _digitos(inscricao) in _digitos(texto_tabela)
    if not encontrada:
        raise PortalFlowError(
            "A tabela de resultados abriu, mas a inscrição pesquisada não foi localizada no texto da tabela. "
            "Nenhum débito foi selecionado."
        )

    log(
        f"PESQUISA CONCLUÍDA: {tipo_inscricao} {inscricao} localizado. "
        f"Linhas visíveis na página: {qtd_linhas}."
    )
    log("PARADA DE SEGURANÇA DA FASE 2: nenhum débito foi selecionado e 'Adicionar à guia' não foi acionado.")
    return ResultadoPesquisaPortal(
        tipo_inscricao=tipo_inscricao,
        inscricao=inscricao,
        competencia=competencia,
        linhas_resultado=qtd_linhas,
        inscricao_encontrada_na_tabela=True,
    )


def salvar_screenshot_erro(page: Page, pasta_raiz: Path) -> Path | None:
    try:
        pasta = pasta_raiz / "screenshots"
        pasta.mkdir(parents=True, exist_ok=True)
        nome = time.strftime("fase2_erro_%Y%m%d_%H%M%S.png")
        destino = pasta / nome
        page.screenshot(path=str(destino), full_page=False)
        return destino
    except Exception:
        return None
