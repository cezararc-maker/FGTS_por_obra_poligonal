from __future__ import annotations

import shutil
from pathlib import Path

from .batch_state import salvar_status
from .models import ItemPlanilha
from .phase5_flow import ResultadoFase5, executar_fase5


def _pasta_inscricao(competencia: str, inscricao: str) -> Path:
    return Path.cwd() / "downloads" / competencia.replace("/", "-") / "".join(ch for ch in inscricao if ch.isdigit())


def achatar_downloads(competencia: str, inscricao: str) -> None:
    """Move arquivos legados da subpasta GUIA para a pasta única da inscrição.

    A partir da Fase 6, todos os arquivos da inscrição ficam juntos. O nome original
    do portal é preservado. Nunca sobrescrevemos silenciosamente um arquivo diferente.
    """
    pasta = _pasta_inscricao(competencia, inscricao)
    subpasta = pasta / "GUIA"
    if not subpasta.exists():
        return

    for origem in subpasta.iterdir():
        if not origem.is_file():
            continue
        destino = pasta / origem.name
        if destino.exists():
            if destino.stat().st_size == origem.stat().st_size:
                origem.unlink()
                continue
            raise RuntimeError(
                f"Já existe um arquivo com o nome original {origem.name!r} na pasta da inscrição, "
                "mas o tamanho é diferente. A automação não irá sobrescrever."
            )
        shutil.move(str(origem), str(destino))

    try:
        subpasta.rmdir()
    except OSError:
        pass


def executar_item_lote(page, *, item: ItemPlanilha, competencia: str, vencimento, log) -> ResultadoFase5:
    salvar_status(
        competencia,
        item.tipo_inscricao,
        item.inscricao,
        status="PROCESSANDO",
    )

    try:
        resultado = executar_fase5(
            page,
            tipo_inscricao=item.tipo_inscricao,
            inscricao=item.inscricao,
            competencia=competencia,
            vencimento=vencimento,
            tag=item.tag,
            log=log,
        )
        achatar_downloads(competencia, item.inscricao)

        pasta = _pasta_inscricao(competencia, item.inscricao)
        caminho_guia = None
        if resultado.guia.caminho:
            caminho_guia = str(pasta / Path(resultado.guia.caminho).name)

        salvar_status(
            competencia,
            item.tipo_inscricao,
            item.inscricao,
            status="CONCLUIDO",
            numero_guia=resultado.numero_guia,
            guia=caminho_guia,
            fgts=resultado.fgts.caminho,
            consignado=resultado.consignado.caminho,
        )
        return resultado
    except Exception as exc:
        try:
            achatar_downloads(competencia, item.inscricao)
        except Exception:
            pass
        salvar_status(
            competencia,
            item.tipo_inscricao,
            item.inscricao,
            status="ERRO",
            erro=str(exc),
        )
        raise
