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

    return list(dict.fromkeys(datas))


def _validar_vencimento(page: Page, vencimento: date, timeout_ms: int = 60_000) -> str:
    esperado = vencimento.strftime("%d/%m/%Y")
    limite = time.monotonic() + timeout_ms / 1000
    ultimas_datas: list[str] = []

    while time.monotonic() < limite:
        datas = _extrair_datas_visiveis(page)
        if datas:
            ultimas_datas = datas
        if esperado in datas:
            return esperado
        if esperado in _texto_pagina(page):
            return esperado
        page.wait_for_timeout(300)

    raise pf.PortalFlowError(
        "A etapa 'Definir Vencimento' não terminou de carregar com o vencimento esperado "
        f"em até {timeout_ms // 1000} segundos: esperado {esperado}. "
        f"Datas encontradas durante a espera: {', '.join(ultimas_datas) if ultimas_datas else 'nenhuma'}."
    )


def _campo_tag(page: Page) -> Locator:
    """Localiza TAG somente por relações estruturais determinísticas.

    Não usa mais proximidade geométrica nem índice global de inputs. Isso evita
    que um Locator baseado em posição passe a apontar para outro campo depois de
    um rerender do Angular.
    """
    # 1) Associação semântica label -> campo, quando o portal a expõe.
    candidatos = pf._visiveis(page.get_by_label(re.compile(r"tag", re.IGNORECASE)))
    campos = []
    for item in candidatos:
        try:
            if item.evaluate("el => ['INPUT','TEXTAREA'].includes(el.tagName)"):
                campos.append(item)
        except Exception:
            pass
    if len(campos) == 1:
        return campos[0]
    if len(campos) > 1:
        raise pf.PortalFlowError("Mais de um campo associado semanticamente ao rótulo TAG foi encontrado.")

    # 2) Atributos funcionais estáveis contendo TAG.
    candidatos = pf._visiveis(
        page.locator(
            "input[name*='tag' i], textarea[name*='tag' i], "
            "input[aria-label*='tag' i], textarea[aria-label*='tag' i]"
        )
    )
    if len(candidatos) == 1:
        return candidatos[0]
    if len(candidatos) > 1:
        raise pf.PortalFlowError("Mais de um campo com atributo funcional de TAG foi encontrado.")

    # 3) Relação estrutural estável: rótulo exato 'Tag (Opcional)' -> primeiro input seguinte.
    # O Locator é reconstruído por esta mesma relação sempre que necessário; não
    # dependemos da posição ordinal dos inputs na página.
    rotulos = pf._visiveis(page.get_by_text(re.compile(r"^Tag\s*\(Opcional\)$", re.IGNORECASE)))
    if len(rotulos) != 1:
        raise pf.PortalFlowError(
            "O rótulo exato 'Tag (Opcional)' não foi localizado de forma única. "
            "A automação não usará aproximação visual para evitar preencher campo incorreto."
        )

    campo = rotulos[0].locator("xpath=following::input[1]")
    if campo.count() != 1 or not campo.is_visible() or not campo.is_enabled():
        raise pf.PortalFlowError(
            "O campo associado estruturalmente a 'Tag (Opcional)' não ficou disponível de forma única."
        )
    return campo


def _preencher_tag(page: Page, tag: str, timeout_ms: int = 5_000) -> None:
    campo = _campo_tag(page)
    campo.fill(tag)
    campo.press("Tab")

    # Angular pode reconstruir o trecho da tela no blur. Por isso NÃO reutilizamos
    # o Locator anterior para validar. Relocalizamos o campo do zero a cada leitura.
    limite = time.monotonic() + timeout_ms / 1000
    ultimo_valor = ""
    while time.monotonic() < limite:
        campo_atual = _campo_tag(page)
        try:
            ultimo_valor = campo_atual.input_value().strip()
        except Exception:
            page.wait_for_timeout(100)
            continue
        if ultimo_valor == tag:
            return
        page.wait_for_timeout(150)

    raise pf.PortalFlowError(
        f"TAG divergente após preenchimento: esperado {tag!r}, recebido {ultimo_valor!r}. "
        "O campo foi relocalizado estruturalmente após o rerender."
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
