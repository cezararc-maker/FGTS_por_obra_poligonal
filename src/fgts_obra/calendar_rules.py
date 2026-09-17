from __future__ import annotations

from datetime import date, timedelta


def calcular_vencimento_mensal(ano: int, mes: int, feriados: set[date] | None = None) -> date:
    """Calcula o vencimento mensal no dia 20 do mês seguinte.

    Se cair em fim de semana ou em data explicitamente informada em ``feriados``,
    antecipa para o dia útil anterior.

    Nesta primeira fase, feriados oficiais ainda não são obtidos automaticamente.
    O parâmetro existe para permitir validação determinística e evolução posterior.
    """
    feriados = feriados or set()

    if mes == 12:
        ano_venc = ano + 1
        mes_venc = 1
    else:
        ano_venc = ano
        mes_venc = mes + 1

    vencimento = date(ano_venc, mes_venc, 20)

    while vencimento.weekday() >= 5 or vencimento in feriados:
        vencimento -= timedelta(days=1)

    return vencimento


def competencia_para_texto(valor: date) -> str:
    return valor.strftime("%m/%Y")
