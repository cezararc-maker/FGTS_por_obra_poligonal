from __future__ import annotations

import json
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
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")


def status_atual(competencia: str, tipo_inscricao: str, inscricao: str) -> str | None:
    dados = carregar_controle(competencia)
    item = dados.get(chave_item(competencia, tipo_inscricao, inscricao))
    if not item:
        return None
    return item.get("status")
