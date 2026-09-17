from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class ItemPlanilha:
    linha: int
    codigo: str
    tipo_inscricao: str
    servico: str
    tag: str
    inscricao: str
    fgts_referencia: float | None
    fgts_aprendiz_referencia: float | None


@dataclass
class ResultadoPlanilha:
    caminho: str
    aba: str
    competencia: str
    vencimento_calculado: date
    vencimento_conferencia: date | None
    itens: list[ItemPlanilha] = field(default_factory=list)
    erros: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)

    @property
    def valida(self) -> bool:
        return not self.erros
