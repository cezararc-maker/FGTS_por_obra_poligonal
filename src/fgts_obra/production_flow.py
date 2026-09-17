from __future__ import annotations

import re
from pathlib import Path

from playwright.sync_api import Download

from . import phase5_flow as p5
from .batch_state import salvar_status
from .models import ItemPlanilha
from .phase6_flow import gerar_zip_competencia, pasta_destino_item


def _nome_seguro(nome: str) -> str:
    nome = re.sub(r'[<>:"/\\|?*]', "_", nome).strip()
    return nome or "arquivo"


def _arquivo_pdf(caminho: Path) -> bool:
    try:
        with caminho.open("rb") as arquivo:
            return arquivo.read(5) == b"%PDF-"
    except Exception:
        return False


def _salvar_guia_direto(
    download: Download | None,
    competencia: str,
    inscricao: str,
    numero_guia: str | None,
):
    if download is None:
        return p5.ResultadoDownload(tipo="GUIA", status="DOWNLOAD AUTOMÁTICO NÃO CAPTURADO", caminho=None)

    pasta = p5._pasta_downloads(competencia, inscricao)
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / _nome_seguro(download.suggested_filename)
    try:
        download.save_as(str(destino))
    except Exception as exc:
        raise p5.pf.PortalFlowError(f"A guia foi emitida, mas o download automático não pôde ser salvo: {exc}") from exc

    if not destino.exists() or destino.stat().st_size <= 0:
        raise p5.pf.PortalFlowError("A guia foi emitida, mas o arquivo automático ficou vazio ou não foi encontrado.")
    if not _arquivo_pdf(destino):
        raise p5.pf.PortalFlowError(f"O download automático salvo em {destino} não possui assinatura de PDF.")

    return p5.ResultadoDownload(tipo="GUIA", status="CONCLUÍDO", caminho=str(destino))


def _log_operacional(log, total: int, indice: int):
    prefixo = f"[{indice}/{total}] "

    def registrar(mensagem: str) -> None:
        if mensagem.startswith("PARADA DE SEGURANÇA"):
            return
        traducoes = {
            "Sessão FGTS Digital confirmada.": "Sessão confirmada.",
            "Abrindo Gestão de Guias...": "Abrindo Gestão de Guias...",
            "Abrindo Emissão de Guia Parametrizada...": "Abrindo Guia Parametrizada...",
            "A tela de Guia Parametrizada já está aberta.": "Guia Parametrizada pronta.",
            "Selecionando competência Inicial/Final na lista:": "Selecionando competência:",
            "Conferindo filtro Vencido...": "Conferindo filtro Vencido...",
            "Abrindo Pesquisa Expandida...": "Abrindo pesquisa...",
            "Pesquisando e aguardando a grade real de débitos...": "Pesquisando débitos...",
            "Marcando o checkbox mestre do cabeçalho e comprovando a seleção das linhas...": "Selecionando débitos...",
            "Aguardando e acionando 'Adicionar à guia'; parada antes de Avançar...": "Adicionando débitos à guia...",
            "Avançando para Selecionar Débitos Consignado...": "Processando consignado...",
            "Tela de consignado carregada. Nenhuma seleção será alterada.": "Consignado carregado sem alteração manual.",
            "Avançando sem alterar consignado para Definir Vencimento...": "Avançando para vencimento...",
            "Aguardando o carregamento da etapa e validando o vencimento do portal...": "Validando vencimento...",
            "Aguardando 'Avançar' em Definir Vencimento...": "Preparando emissão...",
            "Aguardando a etapa Emitir Guia ficar totalmente desbloqueada e estável...": "Aguardando tela de emissão estabilizar...",
            "Emitindo a guia e monitorando o download automático...": "Emitindo guia...",
            "Aguardando a emissão REAL terminar...": "Aguardando conclusão da emissão...",
            "Salvando a própria guia emitida em pasta controlada...": "Salvando guia...",
            "Localizando e baixando os relatórios PDF...": "Baixando relatórios...",
            "Reiniciando o fluxo para deixar o portal pronto para a próxima guia...": "Preparando próxima inscrição...",
        }

        limpa = re.sub(r"^\[\d+/\d+\]\s*", "", mensagem)
        for origem, destino in traducoes.items():
            if limpa.startswith(origem):
                resto = limpa[len(origem):]
                log(prefixo + destino + resto)
                return
        log(prefixo + limpa)

    return registrar


def executar_item_producao(page, *, item: ItemPlanilha, competencia: str, vencimento, log, indice: int, total: int):
    destino = pasta_destino_item(competencia, item.tag, item.inscricao)
    salvar_status(competencia, item.tipo_inscricao, item.inscricao, status="PROCESSANDO")

    pasta_original = p5._pasta_downloads
    salvar_guia_original = p5._salvar_guia_automatica
    p5._pasta_downloads = lambda _competencia, _inscricao: destino
    p5._salvar_guia_automatica = _salvar_guia_direto

    try:
        resultado = p5.executar_fase5(
            page,
            tipo_inscricao=item.tipo_inscricao,
            inscricao=item.inscricao,
            competencia=competencia,
            vencimento=vencimento,
            tag=item.tag,
            log=_log_operacional(log, total, indice),
        )
        salvar_status(
            competencia,
            item.tipo_inscricao,
            item.inscricao,
            status="CONCLUIDO",
            numero_guia=resultado.numero_guia,
            guia=resultado.guia.caminho,
            fgts=resultado.fgts.caminho,
            consignado=resultado.consignado.caminho,
        )
        return resultado
    except Exception as exc:
        salvar_status(
            competencia,
            item.tipo_inscricao,
            item.inscricao,
            status="ERRO",
            erro=str(exc),
        )
        raise
    finally:
        p5._pasta_downloads = pasta_original
        p5._salvar_guia_automatica = salvar_guia_original


__all__ = ["executar_item_producao", "gerar_zip_competencia"]
