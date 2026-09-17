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
        # Mesmo sem paginação identificável, os marcadores + inscrição já provam a grade.
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


def _checkbox_geral_grade(page: Page) -> Locator:
    """Escolhe o checkbox geral pela proximidade do cabeçalho da grade."""
    cabecalhos = pf._visiveis(page.get_by_text("Competência de Apuração", exact=False))
    if not cabecalhos:
        raise pf.PortalFlowError("Cabeçalho 'Competência de Apuração' não foi localizado na grade de resultados.")
    referencia = cabecalhos[0]

    checkboxes = pf._visiveis(page.get_by_role("checkbox"))
    if not checkboxes:
        raise pf.PortalFlowError("Nenhum checkbox visível foi encontrado na grade de resultados.")

    candidato = pf._mais_proximo(referencia, checkboxes, "checkbox geral da grade")
    return candidato


def _marcar_checkbox(controle: Locator, page: Page) -> None:
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

    page.wait_for_timeout(300)
    if not controle.is_checked():
        raise pf.PortalFlowError("O checkbox geral da grade não permaneceu marcado após o clique.")


def _botao_adicionar_guia(page: Page) -> Locator:
    candidatos = pf._visiveis(
        page.get_by_role("button", name=re.compile(r"^Adicionar\s+à\s+guia$", re.IGNORECASE))
    )
    if len(candidatos) == 1:
        return candidatos[0]
    if len(candidatos) > 1:
        raise pf.PortalFlowError("Mais de um botão 'Adicionar à guia' ficou visível.")

    textos = pf._visiveis(page.get_by_text(re.compile(r"^Adicionar\s+à\s+guia$", re.IGNORECASE)))
    if len(textos) == 1:
        atual = textos[0]
        for _ in range(4):
            try:
                if atual.get_attribute("role") == "button" or atual.evaluate("el => el.tagName") == "BUTTON":
                    return atual
                atual = atual.locator("xpath=..")
            except Exception:
                break
    raise pf.PortalFlowError("Botão 'Adicionar à guia' não foi localizado de forma única após a seleção dos débitos.")


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
    log(f"Grade de débitos confirmada. Total informado pelo portal: {total_itens if total_itens is not None else 'não identificado' }.")

    log("[9/10] Marcando o checkbox geral da grade...")
    checkbox = _checkbox_geral_grade(page)
    _marcar_checkbox(checkbox, page)

    log("[10/10] Acionando 'Adicionar à guia' e PARANDO antes de Avançar...")
    adicionar = _botao_adicionar_guia(page)
    adicionar.scroll_into_view_if_needed()
    if not adicionar.is_enabled():
        raise pf.PortalFlowError("O botão 'Adicionar à guia' continuou desabilitado após marcar a grade.")
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
