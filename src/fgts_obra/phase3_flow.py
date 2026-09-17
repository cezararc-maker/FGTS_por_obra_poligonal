from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Callable

from playwright.sync_api import Locator, Page

from . import portal_flow as pf


LogFn = Callable[[str], None]


@dataclass
class ResultadoFase3:
    tipo_inscricao: str
    inscricao: str
    competencia: str
    total_itens: int | None
    selecao_geral_confirmada: bool
    adicionar_guia_acionado: bool


def _texto_pagina(page: Page) -> str:
    try:
        return page.locator("body").inner_text()
    except Exception:
        return ""


def _normalizar(texto: str) -> str:
    return re.sub(r"\s+", " ", texto or "").strip()


def _detectar_grade_resultados(page: Page, inscricao: str, competencia: str) -> int | None:
    """Reconhece a grade real do FGTS Digital sem pressupor uma tag <table>."""
    texto = _texto_pagina(page)
    texto_norm = _normalizar(texto)
    digitos_pagina = pf._digitos(texto)

    marcadores = (
        "Seleção de Débitos",
        "Competência de Apuração",
        "Estabelecimento da Remuneração",
    )
    if not all(marcador in texto_norm for marcador in marcadores):
        return None

    if competencia not in texto_norm:
        return None

    if pf._digitos(inscricao) not in digitos_pagina:
        return None

    paginacao = re.search(r"\b\d+\s*-\s*\d+\s+de\s+(\d+)\s+itens\b", texto_norm, re.IGNORECASE)
    if paginacao:
        return int(paginacao.group(1))
    return None


def _aguardar_grade(page: Page, inscricao: str, competencia: str, timeout_ms: int = 20_000) -> int | None:
    limite = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < limite:
        total = _detectar_grade_resultados(page, inscricao, competencia)
        if total is not None:
            return total
        texto = _normalizar(_texto_pagina(page))
        if (
            "Seleção de Débitos" in texto
            and "Competência de Apuração" in texto
            and competencia in texto
            and pf._digitos(inscricao) in pf._digitos(texto)
        ):
            return None
        page.wait_for_timeout(250)

    raise pf.PortalFlowError(
        "A pesquisa foi enviada, mas a grade real de débitos não pôde ser confirmada em até 20 segundos."
    )


def _caixa(locator: Locator) -> dict | None:
    try:
        return locator.bounding_box()
    except Exception:
        return None


def _checkboxes_grade(page: Page) -> tuple[Locator, list[Locator]]:
    """Identifica o checkbox geral e os checkboxes de linhas pela geometria da grade.

    A grade do FGTS Digital não é uma <table> HTML tradicional. Usamos o cabeçalho
    'Competência de Apuração' como referência visual. O checkbox geral fica à
    esquerda e alinhado verticalmente ao cabeçalho; os checkboxes das linhas ficam
    abaixo dele, praticamente na mesma coluna X.
    """
    cabecalhos = pf._visiveis(page.get_by_text("Competência de Apuração", exact=False))
    if not cabecalhos:
        raise pf.PortalFlowError("Cabeçalho 'Competência de Apuração' não foi localizado na grade de resultados.")

    # Preferimos o cabeçalho que estiver mais próximo da região dos resultados.
    referencia = cabecalhos[-1]
    caixa_ref = _caixa(referencia)
    if not caixa_ref:
        raise pf.PortalFlowError("Não foi possível medir o cabeçalho da grade de resultados.")

    ref_x = caixa_ref["x"]
    ref_y = caixa_ref["y"] + caixa_ref["height"] / 2

    candidatos: list[tuple[float, float, Locator]] = []
    for checkbox in pf._visiveis(page.get_by_role("checkbox")):
        caixa = _caixa(checkbox)
        if not caixa:
            continue
        cx = caixa["x"] + caixa["width"] / 2
        cy = caixa["y"] + caixa["height"] / 2

        # Checkbox da grade deve estar à esquerda do cabeçalho de competência.
        if cx >= ref_x:
            continue

        candidatos.append((cx, cy, checkbox))

    if not candidatos:
        raise pf.PortalFlowError("Nenhum checkbox compatível com a grade de débitos foi localizado.")

    # O geral é o checkbox à esquerda cujo centro está mais alinhado ao cabeçalho.
    candidatos.sort(key=lambda item: abs(item[1] - ref_y))
    geral_x, geral_y, geral = candidatos[0]

    # Exigimos alinhamento vertical razoável para não confundir com filtros acima.
    if abs(geral_y - ref_y) > 70:
        raise pf.PortalFlowError(
            "O checkbox mais próximo do cabeçalho não está alinhado com a grade; a automação parou para evitar seleção incorreta."
        )

    linhas: list[Locator] = []
    for cx, cy, checkbox in candidatos[1:]:
        if cy <= geral_y + 15:
            continue
        if abs(cx - geral_x) > 35:
            continue
        linhas.append(checkbox)

    if not linhas:
        raise pf.PortalFlowError("Os checkboxes das linhas da grade não foram identificados abaixo do checkbox geral.")

    return geral, linhas


def _clicar_checkbox(controle: Locator, page: Page) -> None:
    if controle.is_checked():
        return

    controle_id = controle.get_attribute("id")
    if controle_id:
        labels = pf._visiveis(page.locator(f'label[for="{controle_id}"]'))
        if len(labels) == 1:
            labels[0].click()
        elif len(labels) > 1:
            raise pf.PortalFlowError("Mais de um label foi encontrado para o checkbox geral da grade.")
        else:
            controle.click()
    else:
        controle.click()


def _marcar_e_validar_grade(page: Page) -> int:
    geral, linhas = _checkboxes_grade(page)
    _clicar_checkbox(geral, page)

    limite = time.monotonic() + 3
    while time.monotonic() < limite:
        try:
            geral_marcado = geral.is_checked()
        except Exception:
            # A grade pode rerenderizar após a seleção; relocalizamos.
            geral, linhas = _checkboxes_grade(page)
            geral_marcado = geral.is_checked()

        marcadas = 0
        for linha in linhas:
            try:
                if linha.is_checked():
                    marcadas += 1
            except Exception:
                pass

        if geral_marcado and marcadas > 0:
            return marcadas
        page.wait_for_timeout(150)

    raise pf.PortalFlowError(
        "O clique no checkbox geral não resultou em seleção comprovada das linhas da grade. "
        "A automação parou antes de procurar 'Adicionar à guia'."
    )


def _botao_adicionar_guia(page: Page) -> Locator:
    """Aguarda o controle Adicionar à guia ficar disponível após seleção comprovada."""
    limite = time.monotonic() + 5
    while time.monotonic() < limite:
        candidatos = pf._visiveis(
            page.get_by_role("button", name=re.compile(r"Adicionar\s+à\s+guia", re.IGNORECASE))
        )
        habilitados = [item for item in candidatos if item.is_enabled()]
        if len(habilitados) == 1:
            return habilitados[0]
        if len(habilitados) > 1:
            raise pf.PortalFlowError("Mais de um botão habilitado 'Adicionar à guia' ficou visível.")

        textos = pf._visiveis(page.get_by_text(re.compile(r"Adicionar\s+à\s+guia", re.IGNORECASE)))
        botoes: list[Locator] = []
        for texto in textos:
            atual = texto
            for _ in range(4):
                try:
                    tag = atual.evaluate("el => el.tagName")
                    role = atual.get_attribute("role")
                    if tag == "BUTTON" or role == "button":
                        if atual.is_visible() and atual.is_enabled():
                            botoes.append(atual)
                        break
                    atual = atual.locator("xpath=..")
                except Exception:
                    break
        if len(botoes) == 1:
            return botoes[0]
        if len(botoes) > 1:
            raise pf.PortalFlowError("Mais de um controle habilitado 'Adicionar à guia' foi localizado.")

        page.wait_for_timeout(200)

    raise pf.PortalFlowError(
        "Os débitos foram selecionados, mas o controle 'Adicionar à guia' não apareceu habilitado em até 5 segundos."
    )


def executar_fase3(
    page: Page,
    *,
    tipo_inscricao: str,
    inscricao: str,
    competencia: str,
    log: LogFn,
) -> ResultadoFase3:
    """Fase 3: pesquisa, seleciona todos os débitos e clica em Adicionar à guia.

    Parada obrigatória imediatamente após Adicionar à guia. Esta função NÃO clica em Avançar.
    """
    if tipo_inscricao not in {"CNPJ", "CNO"}:
        raise pf.PortalFlowError(f"Tipo de inscrição não suportado: {tipo_inscricao!r}.")

    if "fgtsdigital.sistema.gov.br" not in page.url.lower():
        raise pf.PortalFlowError("A página ativa não pertence ao FGTS Digital.")

    log("[1/10] Sessão FGTS Digital confirmada.")

    if not pf._visiveis(page.get_by_text("Selecionar Débitos FGTS", exact=False)):
        log("[2/10] Abrindo Gestão de Guias...")
        pf._clicar_texto_priorizado(page, "Gestão de Guias")
        page.wait_for_timeout(400)
        log("[3/10] Abrindo Emissão de Guia Parametrizada...")
        pf._clicar_texto_priorizado(page, "Emissão de Guia Parametrizada")
        page.get_by_text("Selecionar Débitos FGTS", exact=False).first.wait_for(state="visible", timeout=15_000)
    else:
        log("[2/10] A tela de Guia Parametrizada já está aberta.")

    log(f"[4/10] Selecionando competência Inicial/Final na lista: {competencia}...")
    pf._selecionar_competencia(page, "Inicial", competencia)
    pf._selecionar_competencia(page, "Final", competencia)

    log("[5/10] Conferindo filtro Vencido...")
    pf._desmarcar_vencido(page)

    log("[6/10] Abrindo Pesquisa Expandida...")
    pf._expandir_pesquisa(page)

    log(f"[7/10] Selecionando {tipo_inscricao} em Estabelecimento da Remuneração e preenchendo a inscrição...")
    campo = pf._selecionar_tipo_e_campo(page, tipo_inscricao)
    campo.fill(inscricao)
    campo.press("Tab")
    page.wait_for_timeout(250)
    if pf._digitos(campo.input_value()) != pf._digitos(inscricao):
        raise pf.PortalFlowError(
            f"Inscrição divergente após preenchimento: esperado {inscricao}, recebido {campo.input_value()!r}."
        )

    log("[8/10] Pesquisando e aguardando a grade real de débitos...")
    pesquisar = pf._unico_visivel(page.get_by_role("button", name="Pesquisar", exact=True), "Pesquisar")
    pesquisar.click()
    total_itens = _aguardar_grade(page, inscricao, competencia)
    log(
        "Grade de débitos confirmada. Total informado pelo portal: "
        f"{total_itens if total_itens is not None else 'não identificado'}."
    )

    log("[9/10] Marcando o checkbox geral e comprovando a seleção das linhas...")
    linhas_marcadas = _marcar_e_validar_grade(page)
    log(f"Seleção da grade confirmada: {linhas_marcadas} linha(s) visível(is) marcada(s).")

    log("[10/10] Aguardando e acionando 'Adicionar à guia'; parada antes de Avançar...")
    adicionar = _botao_adicionar_guia(page)
    adicionar.scroll_into_view_if_needed()
    adicionar.click()
    page.wait_for_timeout(700)

    log("PARADA DE SEGURANÇA DA FASE 3: 'Adicionar à guia' foi acionado. O botão 'Avançar' NÃO foi clicado.")
    return ResultadoFase3(
        tipo_inscricao=tipo_inscricao,
        inscricao=inscricao,
        competencia=competencia,
        total_itens=total_itens,
        selecao_geral_confirmada=True,
        adicionar_guia_acionado=True,
    )
