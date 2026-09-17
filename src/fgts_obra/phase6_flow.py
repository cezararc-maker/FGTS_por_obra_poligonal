from __future__ import annotations

import re
import shutil
from pathlib import Path

from .batch_state import salvar_status
from .models import ItemPlanilha
from .phase5_flow import ResultadoFase5, executar_fase5


def _nome_pasta_seguro(tag: str, inscricao: str) -> str:
    nome = (tag or "").strip()
    nome = re.sub(r'[<>:"/\\|?*]', "_", nome)
    nome = re.sub(r"\s+", " ", nome).strip(" .")
    if not nome:
        nome = "".join(ch for ch in inscricao if ch.isdigit()) or "SEM_IDENTIFICACAO"
    return nome[:180]


def _pasta_origem_legada(competencia: str, inscricao: str) -> Path:
    return Path.cwd() / "downloads" / competencia.replace("/", "-") / "".join(
        ch for ch in inscricao if ch.isdigit()
    )


def pasta_destino_item(competencia: str, tag: str, inscricao: str) -> Path:
    pasta = (
        Path.home()
        / "Downloads"
        / "FGTS_por_obra_poligonal"
        / competencia.replace("/", "-")
        / _nome_pasta_seguro(tag, inscricao)
    )
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def consolidar_downloads(competencia: str, inscricao: str, tag: str) -> dict[str, str]:
    """Move todos os arquivos gerados para a pasta final da TAG em Downloads.

    O fluxo validado da Fase 5 ainda grava temporariamente no diretório do projeto.
    Ao concluir cada inscrição, a Fase 6 move guia e relatórios para uma única pasta
    na pasta padrão Downloads do usuário, preservando os nomes originais do portal.
    Também absorve a antiga subpasta GUIA quando ela existir.
    """
    origem = _pasta_origem_legada(competencia, inscricao)
    destino = pasta_destino_item(competencia, tag, inscricao)
    movidos: dict[str, str] = {}

    if not origem.exists():
        return movidos

    arquivos = [p for p in origem.rglob("*") if p.is_file()]
    for arquivo in arquivos:
        destino_arquivo = destino / arquivo.name
        if destino_arquivo.exists():
            if destino_arquivo.stat().st_size == arquivo.stat().st_size:
                arquivo.unlink()
                movidos[arquivo.name] = str(destino_arquivo)
                continue
            raise RuntimeError(
                f"Já existe {arquivo.name!r} em {destino}, mas o tamanho é diferente. "
                "A automação não irá sobrescrever silenciosamente."
            )
        shutil.move(str(arquivo), str(destino_arquivo))
        movidos[arquivo.name] = str(destino_arquivo)

    # Remove somente diretórios vazios da estrutura temporária.
    for pasta in sorted((p for p in origem.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
        try:
            pasta.rmdir()
        except OSError:
            pass
    try:
        origem.rmdir()
    except OSError:
        pass

    return movidos


# Compatibilidade com chamadas já existentes na interface da Fase 6.
def achatar_downloads(competencia: str, inscricao: str, tag: str = "") -> None:
    consolidar_downloads(competencia, inscricao, tag)


def _novo_caminho(caminho_antigo: str | None, destino: Path) -> str | None:
    if not caminho_antigo:
        return None
    return str(destino / Path(caminho_antigo).name)


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

        destino = pasta_destino_item(competencia, item.tag, item.inscricao)
        consolidar_downloads(competencia, item.inscricao, item.tag)

        resultado.guia.caminho = _novo_caminho(resultado.guia.caminho, destino)
        resultado.fgts.caminho = _novo_caminho(resultado.fgts.caminho, destino)
        resultado.consignado.caminho = _novo_caminho(resultado.consignado.caminho, destino)

        log(f"Arquivos organizados em: {destino}")

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
        try:
            consolidar_downloads(competencia, item.inscricao, item.tag)
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
