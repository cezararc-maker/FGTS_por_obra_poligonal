from __future__ import annotations

import json
import os
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


def _pasta_controle(competencia: str) -> Path:
    pasta = (
        Path.home()
        / "Downloads"
        / "FGTS_por_obra_poligonal"
        / competencia.replace("/", "-")
    )
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def _arquivo_legado(competencia: str) -> Path:
    return Path.cwd() / "downloads" / competencia.replace("/", "-") / "controle_lote.json"


def _arquivo_controle(competencia: str) -> Path:
    destino = _pasta_controle(competencia) / "controle_lote.json"
    legado = _arquivo_legado(competencia)

    # Migra automaticamente o checkpoint criado nos testes anteriores para não perder
    # a proteção contra reprocessamento das inscrições já concluídas.
    if not destino.exists() and legado.exists():
        try:
            shutil.copy2(legado, destino)
        except Exception:
            pass

    return destino


def chave_item(competencia: str, tipo_inscricao: str, inscricao: str) -> str:
    return f"{competencia}|{tipo_inscricao}|{inscricao}"


def carregar_controle(competencia: str) -> dict[str, Any]:
    caminho = _arquivo_controle(competencia)
    if not caminho.exists():
        return {}
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except Exception:
        return {}


def salvar_status(
    competencia: str,
    tipo_inscricao: str,
    inscricao: str,
    *,
    status: str,
    numero_guia: str | None = None,
    guia: str | None = None,
    fgts: str | None = None,
    consignado: str | None = None,
    erro: str | None = None,
) -> None:
    caminho = _arquivo_controle(competencia)
    dados = carregar_controle(competencia)
    chave = chave_item(competencia, tipo_inscricao, inscricao)
    dados[chave] = {
        "competencia": competencia,
        "tipo_inscricao": tipo_inscricao,
        "inscricao": inscricao,
        "status": status,
        "numero_guia": numero_guia,
        "guia": guia,
        "fgts": fgts,
        "consignado": consignado,
        "erro": erro,
        "atualizado_em": datetime.now().isoformat(timespec="seconds"),
    }
    # A parada imediata pode encerrar o processo no meio desta escrita.
    # A substituição atômica preserva o último checkpoint íntegro.
    temporario = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=caminho.parent,
            prefix="controle_lote_", suffix=".tmp", delete=False,
        ) as arquivo:
            temporario = Path(arquivo.name)
            json.dump(dados, arquivo, ensure_ascii=False, indent=2)
        os.replace(temporario, caminho)
    finally:
        if temporario is not None:
            temporario.unlink(missing_ok=True)


def registro_item(competencia: str, tipo_inscricao: str, inscricao: str) -> dict[str, Any]:
    return carregar_controle(competencia).get(chave_item(competencia, tipo_inscricao, inscricao), {})


def registrar_guia_recuperada(
    competencia: str, tipo_inscricao: str, inscricao: str, *,
    numero_guia: str | None, guia: str,
) -> None:
    """Registra confirmação manual sem declarar relatórios ou lote concluídos."""
    pdf = Path(guia)
    if not pdf.is_file() or pdf.stat().st_size == 0:
        raise ValueError("O PDF selecionado não existe ou está vazio.")
    with pdf.open("rb") as arquivo:
        if arquivo.read(5) != b"%PDF-":
            raise ValueError("O arquivo selecionado não é um PDF válido.")
    atual = registro_item(competencia, tipo_inscricao, inscricao)
    if atual.get("status") == "CONCLUIDO":
        raise ValueError("Esta inscrição já está concluída no controle.")
    salvar_status(
        competencia, tipo_inscricao, inscricao, status="GUIA_RECUPERADA",
        numero_guia=numero_guia or atual.get("numero_guia"), guia=str(pdf.resolve()),
        fgts=atual.get("fgts"), consignado=atual.get("consignado"),
        erro="Guia confirmada manualmente; relatórios e conclusão ainda pendentes.",
    )


def registrar_guia_nao_encontrada(competencia: str, tipo_inscricao: str, inscricao: str) -> None:
    """Libera nova tentativa somente após a conferência explícita do operador."""
    atual = registro_item(competencia, tipo_inscricao, inscricao)
    if atual.get("status") not in {"PROCESSANDO", "CONFERIR_EMISSAO"}:
        raise ValueError("Esta inscrição não está aguardando conferência de emissão.")
    guia = atual.get("guia")
    if guia and Path(guia).is_file():
        raise ValueError("Já existe um PDF de guia registrado para esta inscrição.")
    salvar_status(
        competencia, tipo_inscricao, inscricao, status="LIBERADO_REEMISSAO",
        erro="Operador conferiu no portal e não encontrou guia; nova tentativa liberada.",
    )


def status_atual(competencia: str, tipo_inscricao: str, inscricao: str) -> str | None:
    dados = carregar_controle(competencia)
    item = dados.get(chave_item(competencia, tipo_inscricao, inscricao))
    if not item:
        return None
    return item.get("status")
