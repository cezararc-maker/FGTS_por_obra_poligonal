from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import date
from typing import Callable

from playwright.sync_api import Locator, Page

from . import portal_flow as pf
from .phase3_flow import executar_fase3


LogFn = Callable[[str], None]


@dataclass
class ResultadoFase4:
    tipo_inscricao: str
    inscricao: str
    competencia: str
    vencimento_esperado: str
    vencimento_portal: str
    tag: str
    tela_definir_vencimento_confirmada: bool
    tag_preenchida: bool


def _texto_pagina(page: Page) -> str:
    try:
        return page.locator("body").inner_text()
    except Exception:
        return ""


def _aguardar_texto(page: Page, texto: str, timeout_ms: int = 15_000) -> None:
    limite = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < limite:
        if texto in _texto_pagina(page):
            return
        page.wait_for_timeout(250)
    raise pf.PortalFlowError(f"A tela esperada '{texto}' não apareceu em até {timeout_ms // 1000} segundos.")


def _botao_avancar(page: Page) -> Locator:
    candidatos = pf._visiveis(page.get_by_role("button", name="Avançar", exact=True))
    habilitados = [item for item in candidatos if item.is_enabled()]
    if len(habilitados) == 1:
        return habilitados[0]
    if len(habilitados) > 1:
        raise pf.PortalFlowError("Mais de um botão 'Avançar' habilitado ficou visível.")
    raise pf.PortalFlowError("Botão 'Avançar' habilitado não foi localizado de forma única.")


def _extrair_datas_visiveis(page: Page) -> list[str]:
    datas: list[str] = []

    try:
        texto = _texto_pagina(page)
        datas.extend(re.findall(r"\b\d{2}/\d{2}/\d{4}\b", texto))
    except Exception:
        pass

    # Alguns componentes do portal mantêm a data somente no value do input,
    # sem incluí-la imediatamente no innerText da página.
    try:
        inputs = pf._visiveis(page.locator("input"))
        for campo in inputs:
            try:
                valor = campo.input_value().strip()
            except Exception:
                continue
            datas.extend(re.findall(r"\b\d{2}/\d{2}/\d{4}\b", valor))
    except Exception:
        pass

    # Preserva a ordem e remove duplicidades.
    return list(dict.fromkeys(datas))


def _validar_vencimento(page: Page, vencimento: date, timeout_ms: int = 60_000) -> str:
    """Aguarda a etapa Definir Vencimento terminar de carregar e valida a data.

    Essa tela pode levar mais tempo que as anteriores. Enquanto os totais são
    calculados, o campo 'Vencimento da Guia' pode permanecer vazio. Por isso a
    validação é baseada em estado real, e não em uma pausa fixa.
    """
    esperado = vencimento.strftime("%d/%m/%Y")
    limite = time.monotonic() + timeout_ms / 1000
    ultimas_datas: list[str] = []

    while time.monotonic() < limite:
        datas = _extrair_datas_visiveis(page)
        if datas:
            ultimas_datas = datas
        if esperado in datas:
            return esperado

        # Fallback adicional para componentes que renderizam o valor fora de input.
        if esperado in _texto_pagina(page):
            return esperado

        page.wait_for_timeout(300)

    raise pf.PortalFlowError(
        "A etapa 'Definir Vencimento' não terminou de carregar com o vencimento esperado "
        f"em até {timeout_ms // 1000} segundos: esperado {esperado}. "
        f"Datas encontradas durante a espera: {', '.join(ultimas_datas) if ultimas_datas else 'nenhuma'}."
    )


def _campo_tag(page: Page) -> Locator:
    # Primeiro tenta associação semântica direta. O portal usa 'Tag (Opcional)',
    # portanto não exigimos igualdade exata com 'TAG'.
    candidatos = pf._visiveis(page.get_by_label(re.compile(r"tag", re.IGNORECASE)))
    campos = [item for item in candidatos if item.evaluate("el => ['INPUT','TEXTAREA'].includes(el.tagName)")]
    if len(campos) == 1:
        return campos[0]
    if len(campos) > 1:
        raise pf.PortalFlowError("Mais de um campo associado ao rótulo TAG foi encontrado.")

    # Depois tenta atributos estáveis contendo 'tag'.
    candidatos = pf._visiveis(
        page.locator(
            "input[name*='tag' i], textarea[name*='tag' i], "
            "input[id*='tag' i], textarea[id*='tag' i], "
            "input[aria-label*='tag' i], textarea[aria-label*='tag' i]"
        )
    )
    if len(candidatos) == 1:
        return candidatos[0]
    if len(candidatos) > 1:
        raise pf.PortalFlowError("Mais de um campo candidato para TAG foi encontrado na tela.")

    # Fallback controlado: procura o texto 'Tag (Opcional)' e o campo visível mais próximo.
    rotulos = pf._visiveis(page.get_by_text(re.compile(r"^Tag(?:\s*\(Opcional\))?$", re.IGNORECASE)))
    if len(rotulos) != 1:
        raise pf.PortalFlowError("O rótulo TAG não foi localizado de forma única na etapa Definir Vencimento.")

    rotulo = rotulos[0]
    rx, ry = pf._centro(rotulo)
    candidatos = pf._visiveis(page.locator("input:enabled, textarea:enabled"))
    medidos: list[tuple[float, Locator]] = []
    for campo in candidatos:
        try:
            cx, cy = pf._centro(campo)
        except Exception:
            continue
        if cy < ry - 20:
            continue
        distancia = ((cx - rx) ** 2 + (cy - ry) ** 2) ** 0.5
        medidos.append((distancia, campo))

    if not medidos:
        raise pf.PortalFlowError("Nenhum campo editável foi associado com segurança ao rótulo TAG.")
    medidos.sort(key=lambda item: item[0])
    if len(medidos) > 1 and abs(medidos[1][0] - medidos[0][0]) < 5:
        raise pf.PortalFlowError("Dois campos ficaram praticamente empatados como candidatos ao campo TAG.")
    return medidos[0][1]


def _preencher_tag(page: Page, tag: str) -> None:
    campo = _campo_tag(page)
    campo.fill(tag)
    campo.press("Tab")
    page.wait_for_timeout(250)
    recebido = campo.input_value().strip()
    if recebido != tag:
        raise pf.PortalFlowError(
            f"TAG divergente após preenchimento: esperado {tag!r}, recebido {recebido!r}."
        )


def executar_fase4(
    page: Page,
    *,
    tipo_inscricao: str,
    inscricao: str,
    competencia: str,
    vencimento: date,
    tag: str,
    log: LogFn,
) -> ResultadoFase4:
    """Executa até Definir Vencimento, preenche TAG e para antes de Emitir Guia."""

    log("[1/6] Executando o fluxo validado da Fase 3...")
    executar_fase3(
        page,
        tipo_inscricao=tipo_inscricao,
        inscricao=inscricao,
        competencia=competencia,
        log=log,
    )

    log("[2/6] Avançando para Selecionar Débitos Consignado...")
    avancar = _botao_avancar(page)
    avancar.click()
    _aguardar_texto(page, "Selecionar Débitos Consignado")

    log("[3/6] Tela de consignado carregada. Nenhuma seleção será alterada.")
    # Conforme regra do processo, os débitos consignados já vêm selecionados
    # automaticamente de acordo com os CPFs escolhidos no FGTS.
    page.wait_for_timeout(500)

    log("[4/6] Avançando sem alterar consignado para Definir Vencimento...")
    avancar = _botao_avancar(page)
    avancar.click()
    _aguardar_texto(page, "Definir Vencimento")

    log("[5/6] Aguardando o carregamento da etapa e validando o vencimento do portal...")
    venc_portal = _validar_vencimento(page, vencimento, timeout_ms=60_000)

    log(f"[6/6] Preenchendo TAG da planilha: {tag!r}...")
    _preencher_tag(page, tag)

    if not pf._visiveis(page.get_by_text("Emitir Guia", exact=False)):
        raise pf.PortalFlowError(
            "A TAG foi preenchida, mas a etapa 'Emitir Guia' não ficou identificável. "
            "A automação parou sem emitir a guia."
        )

    log("PARADA DE SEGURANÇA DA FASE 4: vencimento validado e TAG preenchida. 'Emitir Guia' NÃO foi acionado.")
    return ResultadoFase4(
        tipo_inscricao=tipo_inscricao,
        inscricao=inscricao,
        competencia=competencia,
        vencimento_esperado=vencimento.strftime("%d/%m/%Y"),
        vencimento_portal=venc_portal,
        tag=tag,
        tela_definir_vencimento_confirmada=True,
        tag_preenchida=True,
    )
