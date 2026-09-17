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
        super().__init__(
            f"O download do relatório em PDF de {tipo} não iniciou dentro da janela de aproximadamente 5 segundos."
        )
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
    numero_guia: str
    fgts: ResultadoDownload
    consignado: ResultadoDownload
    reiniciado: bool


def _texto_pagina(page: Page) -> str:
    try:
        return page.locator("body").inner_text()
    except Exception:
        return ""


def _overlay_carregamento_visivel(page: Page) -> bool:
    for seletor in ("app-loading .backdrop", "app-loading", ".backdrop"):
        try:
            if pf._visiveis(page.locator(seletor)):
                return True
        except Exception:
            pass
    return False


def _aguardar_sem_overlay(page: Page, timeout_ms: int = 90_000) -> None:
    limite = time.monotonic() + timeout_ms / 1000
    inicio_estavel: float | None = None

    while time.monotonic() < limite:
        if not _overlay_carregamento_visivel(page):
            if inicio_estavel is None:
                inicio_estavel = time.monotonic()
            elif time.monotonic() - inicio_estavel >= 0.8:
                return
        else:
            inicio_estavel = None
        page.wait_for_timeout(200)

    raise pf.PortalFlowError(
        f"O portal permaneceu com a camada de carregamento ativa por mais de {timeout_ms // 1000} segundos."
    )


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


def _aguardar_etapa_emitir_guia(page: Page, timeout_ms: int = 90_000) -> Locator:
    limite = time.monotonic() + timeout_ms / 1000

    while time.monotonic() < limite:
        candidatos = pf._visiveis(page.locator("button.br-button.primary.wizard-btn"))
        emitir: list[Locator] = []
        for item in candidatos:
            try:
                if item.inner_text().strip() == "Emitir Guia" and item.is_enabled():
                    emitir.append(item)
            except Exception:
                pass

        if len(emitir) > 1:
            raise pf.PortalFlowError("Mais de um botão real 'Emitir Guia' habilitado ficou visível.")

        if len(emitir) == 1 and not _overlay_carregamento_visivel(page):
            _aguardar_sem_overlay(page, timeout_ms=10_000)
            return emitir[0]

        page.wait_for_timeout(300)

    raise pf.PortalFlowError(
        "A etapa Emitir Guia não ficou pronta para clique em até 90 segundos. "
        "O botão pode estar visível, mas ainda coberto pela camada de carregamento."
    )


def _extrair_numero_guia(page: Page) -> str | None:
    """Extrai o identificador exibido ao lado da TAG após a emissão.

    Exemplo observado no portal: 0126091761792989-0.
    O hífen diferencia o número da guia de CNPJ/CNO/CPF comuns exibidos na tela.
    """
    texto = _texto_pagina(page)
    candidatos = re.findall(r"(?<!\d)(\d{12,25}-\d{1,4})(?!\d)", texto)
    if not candidatos:
        return None

    # Na etapa pós-emissão o número da guia aparece na região superior, ao lado da TAG.
    # Se houver mais de um candidato, evitamos escolher silenciosamente.
    unicos = list(dict.fromkeys(candidatos))
    if len(unicos) == 1:
        return unicos[0]
    return None


def _aguardar_emissao_confirmada(page: Page, timeout_ms: int = 90_000) -> str:
    """Aguarda a emissão real, sem aplicar o timeout curto dos downloads.

    A emissão só é considerada concluída quando o overlay desapareceu e o número
    da guia passou a existir na página. 'Reiniciar' sozinho não é suficiente.
    """
    limite = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < limite:
        if _overlay_carregamento_visivel(page):
            page.wait_for_timeout(300)
            continue

        numero = _extrair_numero_guia(page)
        if numero:
            return numero

        page.wait_for_timeout(400)

    raise pf.PortalFlowError(
        "Após 'Emitir Guia', o portal não apresentou o número da guia em até 90 segundos. "
        "A automação não assumirá que a emissão terminou apenas porque o botão 'Reiniciar' apareceu."
    )


def _texto_elemento(locator: Locator) -> str:
    partes: list[str] = []
    try:
        partes.append(locator.inner_text())
    except Exception:
        pass
    for atributo in ("title", "aria-label", "name", "id", "class", "href"):
        try:
            valor = locator.get_attribute(atributo)
            if valor:
                partes.append(valor)
        except Exception:
            pass
    try:
        partes.append(locator.evaluate("el => el.outerHTML"))
    except Exception:
        pass
    return " ".join(partes).lower()


def _controle_pdf_secao(page: Page, secao: str) -> Locator | None:
    """Localiza o controle PDF dentro da seção FGTS ou Consignado.

    O portal atual exibe ícones circulares, não necessariamente um botão com o
    texto 'Imprimir Relatório em PDF'. A busca fica restrita ao menor contêiner
    estrutural da seção que contenha um descendente clicável identificável como PDF.
    """
    titulos = pf._visiveis(page.get_by_text(secao, exact=True))
    if not titulos:
        return None

    candidatos_encontrados: list[Locator] = []
    for titulo in titulos:
        atual = titulo
        for _ in range(6):
            try:
                atual = atual.locator("xpath=..")
                clicaveis = pf._visiveis(atual.locator("button, a, [role='button']"))
            except Exception:
                break

            pdfs: list[Locator] = []
            for controle in clicaveis:
                descricao = _texto_elemento(controle)
                if "pdf" in descricao:
                    pdfs.append(controle)

            if len(pdfs) == 1:
                candidatos_encontrados.append(pdfs[0])
                break
            if len(pdfs) > 1:
                # Em FGTS pode haver PDF + CSV; só aceitamos um controle que seja
                # inequivocamente PDF. Se mais de um contiver 'pdf', não adivinhamos.
                return None

    # Remove duplicidades geométricas do mesmo controle encontrado por títulos repetidos.
    unicos: list[Locator] = []
    chaves: set[str] = set()
    for item in candidatos_encontrados:
        try:
            caixa = item.bounding_box()
            if not caixa:
                continue
            chave = f"{round(caixa['x'])}:{round(caixa['y'])}:{round(caixa['width'])}:{round(caixa['height'])}"
        except Exception:
            continue
        if chave not in chaves:
            chaves.add(chave)
            unicos.append(item)

    if len(unicos) == 1:
        return unicos[0]
    return None


def _aguardar_controle_pdf(page: Page, secao: str, timeout_ms: int = 20_000) -> Locator | None:
    limite = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < limite:
        if _overlay_carregamento_visivel(page):
            page.wait_for_timeout(250)
            continue
        controle = _controle_pdf_secao(page, secao)
        if controle is not None:
            return controle
        page.wait_for_timeout(300)
    return None


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

    # save_as só retorna depois de o arquivo ter sido concluído pelo navegador.
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
    log("[1/7] Executando o fluxo validado até vencimento/TAG...")
    executar_fase4(
        page,
        tipo_inscricao=tipo_inscricao,
        inscricao=inscricao,
        competencia=competencia,
        vencimento=vencimento,
        tag=tag,
        log=log,
    )

    log("[2/7] Aguardando 'Avançar' em Definir Vencimento...")
    avancar = _aguardar_botao_habilitado(page, "Avançar", timeout_ms=60_000)
    avancar.click()

    log("[3/7] Aguardando a etapa Emitir Guia ficar totalmente desbloqueada...")
    emitir = _aguardar_etapa_emitir_guia(page, timeout_ms=90_000)

    log("[4/7] Emitindo a guia...")
    emitir.click(timeout=10_000)

    log("[5/7] Aguardando a emissão REAL terminar e o número da guia aparecer...")
    numero_guia = _aguardar_emissao_confirmada(page, timeout_ms=90_000)
    log(f"Guia emitida confirmada pelo portal. Número da guia: {numero_guia}.")

    log("[6/7] Localizando e baixando o relatório PDF do FGTS...")
    pdf_fgts = _aguardar_controle_pdf(page, "FGTS", timeout_ms=20_000)
    if pdf_fgts is None:
        raise pf.PortalFlowError(
            "A guia foi emitida e o número da guia foi confirmado, mas o controle PDF da seção FGTS "
            "não pôde ser identificado de forma determinística em até 20 segundos."
        )
    fgts = _baixar_relatorio(page, pdf_fgts, "FGTS", competencia, inscricao)

    consignado = ResultadoDownload(tipo="CONSIGNADO", status="NÃO HÁ CONSIGNADO", caminho=None)
    pdf_consignado = _aguardar_controle_pdf(page, "Consignado", timeout_ms=3_000)
    if pdf_consignado is not None:
        log("Baixando relatório PDF do Consignado...")
        consignado = _baixar_relatorio(page, pdf_consignado, "CONSIGNADO", competencia, inscricao)
    else:
        log("Consignado: nenhum controle PDF identificado; tratando como sem relatório de consignado.")

    log("[7/7] Reiniciando o fluxo para deixar o portal pronto para a próxima guia...")
    _reiniciar(page)

    return ResultadoFase5(
        tipo_inscricao=tipo_inscricao,
        inscricao=inscricao,
        competencia=competencia,
        guia_emitida=True,
        numero_guia=numero_guia,
        fgts=fgts,
        consignado=consignado,
        reiniciado=True,
    )
