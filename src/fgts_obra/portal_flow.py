from __future__ import annotations

import math
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

    if _visiveis(page.get_by_text("Estabelecimento da Remuneração", exact=True)):
        return

    ocultar = _visiveis(page.get_by_role("button", name="Ocultar Pesquisa Expandida", exact=True))
    if len(ocultar) == 1:
        return
    raise PortalFlowError("Não foi possível determinar se a Pesquisa Expandida está aberta ou fechada.")


def _centro(locator: Locator) -> tuple[float, float]:
    caixa = locator.bounding_box()
    if not caixa:
        raise PortalFlowError("Não foi possível obter a posição visual de um elemento da pesquisa expandida.")
    return (caixa["x"] + caixa["width"] / 2, caixa["y"] + caixa["height"] / 2)


def _mais_proximo(referencia: Locator, candidatos: list[Locator], descricao: str) -> Locator:
    if not candidatos:
        raise PortalFlowError(f"Nenhum elemento visível encontrado para {descricao}.")

    rx, ry = _centro(referencia)
    medidos: list[tuple[float, Locator]] = []
    for candidato in candidatos:
        try:
            cx, cy = _centro(candidato)
        except PortalFlowError:
            continue
        medidos.append((math.hypot(cx - rx, cy - ry), candidato))

    if not medidos:
        raise PortalFlowError(f"Não foi possível medir a posição dos candidatos de {descricao}.")

    medidos.sort(key=lambda item: item[0])
    if len(medidos) > 1 and abs(medidos[1][0] - medidos[0][0]) < 4:
        raise PortalFlowError(f"Dois elementos ficaram praticamente empatados para {descricao}; a automação parou.")
    return medidos[0][1]


def _titulo_estabelecimento(page: Page) -> Locator:
    return _unico_visivel(
        page.get_by_text("Estabelecimento da Remuneração", exact=True),
        "Estabelecimento da Remuneração",
    )


def _selecionar_tipo_estabelecimento(page: Page, tipo: str) -> Locator:
    """Seleciona CNPJ/CNO no bloco correto antes de procurar o campo.

    O campo de inscrição só é habilitado/exibido depois da escolha do tipo.
    Como existem CNPJ/CNO em outros blocos, usamos o título de Estabelecimento
    da Remuneração como âncora visual e escolhemos a opção mais próxima dele.
    """
    titulo = _titulo_estabelecimento(page)
    opcoes = _visiveis(page.get_by_text(tipo, exact=True))
    opcao = _mais_proximo(
        titulo,
        opcoes,
        f"opção {tipo} de Estabelecimento da Remuneração",
    )

    tx, ty = _centro(titulo)
    ox, oy = _centro(opcao)
    if oy <= ty:
        raise PortalFlowError(
            f"A opção {tipo} selecionada não está abaixo do título 'Estabelecimento da Remuneração'."
        )

    opcao.click()
    page.wait_for_timeout(250)
    return titulo


def _aguardar_campo_estabelecimento(page: Page, titulo: Locator) -> Locator:
    """Aguarda o input real do Estabelecimento da Remuneração após escolher CNPJ/CNO."""
    seletor = "input[name='nrEstabelecimentoRemuneracao']"
    limite = time.monotonic() + 5

    while time.monotonic() < limite:
        campos = _visiveis(page.locator(seletor))
        if len(campos) == 1:
            campo = campos[0]
            try:
                if campo.is_enabled():
                    tx, ty = _centro(titulo)
                    cx, cy = _centro(campo)
                    if cy > ty:
                        return campo
            except Exception:
                pass
        elif len(campos) > 1:
            raise PortalFlowError(
                "Mais de um input com name='nrEstabelecimentoRemuneracao' ficou visível; a automação parou."
            )

        page.wait_for_timeout(150)

    raise PortalFlowError(
        "Após selecionar o tipo de inscrição, o campo name='nrEstabelecimentoRemuneracao' "
        "não apareceu habilitado em até 5 segundos."
    )


def _selecionar_tipo_e_campo(page: Page, tipo: str) -> Locator:
    titulo = _selecionar_tipo_estabelecimento(page, tipo)
    return _aguardar_campo_estabelecimento(page, titulo)


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

    log(
        f"[7/8] Selecionando {tipo_inscricao} em Estabelecimento da Remuneração, "
        "aguardando o campo e preenchendo a inscrição..."
    )
    campo = _selecionar_tipo_e_campo(page, tipo_inscricao)
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