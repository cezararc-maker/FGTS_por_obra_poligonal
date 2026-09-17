from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from playwright.sync_api import Download, Locator, Page, TimeoutError as PlaywrightTimeoutError

from . import portal_flow as pf
from .phase4_flow import executar_fase4


LogFn = Callable[[str], None]


class DownloadRelatorioTimeout(RuntimeError):
    def __init__(self, tipo: str) -> None:
        super().__init__(f"O download do relatório em PDF de {tipo} não iniciou/concluiu dentro da janela de 5 segundos.")
        self.tipo = tipo


@dataclass
class ResultadoDownload:
    tipo: str
    status: str
    caminho: str | None = None


@dataclass
class ResultadoFase5:
    tipo_inscricao: str
    inscricao: str
    competencia: str
    guia_emitida: bool
    fgts: ResultadoDownload
    consignado: ResultadoDownload
    reiniciado: bool


def _texto_pagina(page: Page) -> str:
    try:
        return page.locator("body").inner_text()
    except Exception:
        return ""


def _botao_unico(page: Page, nome: str) -> Locator:
    candidatos = pf._visiveis(page.get_by_role("button", name=nome, exact=True))
    if len(candidatos) == 1:
        return candidatos[0]
    if len(candidatos) > 1:
        raise pf.PortalFlowError(f"Mais de um botão '{nome}' ficou visível.")
    raise pf.PortalFlowError(f"Botão '{nome}' não foi localizado de forma única.")


def _aguardar_botao_habilitado(page: Page, nome: str, timeout_ms: int = 60_000) -> Locator:
    limite = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < limite:
        candidatos = pf._visiveis(page.get_by_role("button", name=nome, exact=True))
        habilitados = [item for item in candidatos if item.is_enabled()]
        if len(habilitados) == 1:
            return habilitados[0]
        if len(habilitados) > 1:
            raise pf.PortalFlowError(f"Mais de um botão '{nome}' habilitado ficou visível.")
        page.wait_for_timeout(300)
    raise pf.PortalFlowError(f"Botão '{nome}' não ficou habilitado em até {timeout_ms // 1000} segundos.")


def _aguardar_etapa_emitir_guia(page: Page, timeout_ms: int = 60_000) -> Locator:
    limite = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < limite:
        botoes = pf._visiveis(page.get_by_role("button", name="Emitir Guia", exact=True))
        habilitados = [item for item in botoes if item.is_enabled()]
        if len(habilitados) == 1:
            return habilitados[0]
        if len(habilitados) > 1:
            raise pf.PortalFlowError("Mais de um botão 'Emitir Guia' habilitado ficou visível.")
        page.wait_for_timeout(300)
    raise pf.PortalFlowError("A etapa final não liberou o botão 'Emitir Guia' em até 60 segundos.")


def _aguardar_pos_emissao(page: Page, timeout_ms: int = 90_000) -> None:
    limite = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < limite:
        botoes_pdf = pf._visiveis(page.get_by_role("button", name=re.compile(r"Imprimir Relatório em PDF", re.IGNORECASE)))
        if botoes_pdf:
            return
        if pf._visiveis(page.get_by_text("Reiniciar", exact=True)):
            return
        page.wait_for_timeout(400)
    raise pf.PortalFlowError("Após 'Emitir Guia', o portal não liberou os relatórios/reinício em até 90 segundos.")


def _botoes_relatorio_pdf(page: Page) -> list[Locator]:
    candidatos = pf._visiveis(page.get_by_role("button", name=re.compile(r"Imprimir Relatório em PDF", re.IGNORECASE)))
    if not candidatos:
        candidatos = pf._visiveis(page.get_by_text(re.compile(r"Imprimir Relatório em PDF", re.IGNORECASE)))

    medidos: list[tuple[float, Locator]] = []
    vistos: set[str] = set()
    for item in candidatos:
        try:
            caixa = item.bounding_box()
            if not caixa:
                continue
            chave = f"{round(caixa['x'])}:{round(caixa['y'])}:{round(caixa['width'])}:{round(caixa['height'])}"
            if chave in vistos:
                continue
            vistos.add(chave)
            medidos.append((caixa["y"], item))
        except Exception:
            continue
    medidos.sort(key=lambda par: par[0])
    return [item for _, item in medidos]


def _pasta_downloads(competencia: str, inscricao: str) -> Path:
    pasta = Path.cwd() / "downloads" / competencia.replace("/", "-") / re.sub(r"\D", "", inscricao)
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def _nome_seguro(nome: str) -> str:
    nome = re.sub(r'[<>:"/\\|?*]', "_", nome).strip()
    return nome or "relatorio.pdf"


def _baixar_relatorio(page: Page, botao: Locator, tipo: str, competencia: str, inscricao: str) -> ResultadoDownload:
    pasta = _pasta_downloads(competencia, inscricao)
    try:
        with page.expect_download(timeout=5_000) as info:
            botao.scroll_into_view_if_needed()
            botao.click()
        download: Download = info.value
    except PlaywrightTimeoutError as exc:
        raise DownloadRelatorioTimeout(tipo) from exc

    sugerido = _nome_seguro(download.suggested_filename)
    destino = pasta / f"{tipo}_{sugerido}"

    try:
        download.save_as(str(destino))
    except Exception as exc:
        raise DownloadRelatorioTimeout(tipo) from exc

    if not destino.exists() or destino.stat().st_size <= 0:
        raise DownloadRelatorioTimeout(tipo)

    return ResultadoDownload(tipo=tipo, status="CONCLUÍDO", caminho=str(destino))


def _reiniciar(page: Page, timeout_ms: int = 30_000) -> None:
    candidatos = pf._visiveis(page.get_by_role("button", name="Reiniciar", exact=True))
    if not candidatos:
        candidatos = pf._visiveis(page.get_by_text("Reiniciar", exact=True))
    if len(candidatos) != 1:
        raise pf.PortalFlowError("Controle 'Reiniciar' não foi localizado de forma única após a emissão.")
    candidatos[0].click()

    limite = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < limite:
        texto = _texto_pagina(page)
        if "Selecionar Débitos FGTS" in texto or "Emissão de Guia Parametrizada" in texto:
            return
        page.wait_for_timeout(300)
    raise pf.PortalFlowError("O portal não retornou à tela inicial da Guia Parametrizada após 'Reiniciar'.")


def executar_fase5(
    page: Page,
    *,
    tipo_inscricao: str,
    inscricao: str,
    competencia: str,
    vencimento,
    tag: str,
    log: LogFn,
) -> ResultadoFase5:
    log("[1/6] Executando o fluxo validado até vencimento/TAG...")
    executar_fase4(
        page,
        tipo_inscricao=tipo_inscricao,
        inscricao=inscricao,
        competencia=competencia,
        vencimento=vencimento,
        tag=tag,
        log=log,
    )

    log("[2/6] Aguardando 'Avançar' em Definir Vencimento...")
    avancar = _aguardar_botao_habilitado(page, "Avançar", timeout_ms=60_000)
    avancar.click()

    log("[3/6] Aguardando a etapa Emitir Guia ficar pronta...")
    emitir = _aguardar_etapa_emitir_guia(page, timeout_ms=60_000)

    log("[4/6] Emitindo a guia...")
    emitir.click()

    log("[5/6] Aguardando o portal concluir a emissão e liberar os relatórios...")
    _aguardar_pos_emissao(page)

    botoes = _botoes_relatorio_pdf(page)
    if not botoes:
        raise pf.PortalFlowError("A guia foi emitida, mas nenhum botão 'Imprimir Relatório em PDF' ficou disponível.")

    log("[6/6] Baixando relatório em PDF do FGTS...")
    fgts = _baixar_relatorio(page, botoes[0], "FGTS", competencia, inscricao)

    consignado = ResultadoDownload(tipo="CONSIGNADO", status="NÃO HÁ CONSIGNADO", caminho=None)
    botoes = _botoes_relatorio_pdf(page)
    if len(botoes) >= 2:
        log("Baixando relatório em PDF do Consignado...")
        consignado = _baixar_relatorio(page, botoes[1], "CONSIGNADO", competencia, inscricao)
    else:
        log("Consignado: nenhum relatório em PDF disponível para esta guia.")

    log("Reiniciando o fluxo para deixar o portal pronto para a próxima guia...")
    _reiniciar(page)

    return ResultadoFase5(
        tipo_inscricao=tipo_inscricao,
        inscricao=inscricao,
        competencia=competencia,
        guia_emitida=True,
        fgts=fgts,
        consignado=consignado,
        reiniciado=True,
    )
