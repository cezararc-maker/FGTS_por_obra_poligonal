from __future__ import annotations

from datetime import date, timedelta


def _pascoa(ano: int) -> date:
    """Retorna a data da Páscoa pelo algoritmo gregoriano de Meeus."""
    a = ano % 19
    b = ano // 100
    c = ano % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = (h + l - 7 * m + 114) % 31 + 1
    return date(ano, mes, dia)


def feriados_nacionais_br(ano: int) -> set[date]:
    """Feriados nacionais que podem antecipar o vencimento do FGTS."""
    feriados = {
        date(ano, 1, 1),
        date(ano, 4, 21),
        date(ano, 5, 1),
        date(ano, 9, 7),
        date(ano, 10, 12),
        date(ano, 11, 2),
        date(ano, 11, 15),
        date(ano, 12, 25),
    }
    if ano >= 2024:
        feriados.add(date(ano, 11, 20))

    # Sexta-feira da Paixão também é feriado nacional.
    feriados.add(_pascoa(ano) - timedelta(days=2))
    return feriados


def calcular_vencimento_mensal(ano: int, mes: int, feriados: set[date] | None = None) -> date:
    """Calcula o vencimento mensal no dia 20 do mês seguinte.

    Se cair em fim de semana ou em feriado nacional, antecipa para o dia útil
    anterior. ``feriados`` permite acrescentar datas excepcionais do portal.
    """
    if mes == 12:
        ano_venc = ano + 1
        mes_venc = 1
    else:
        ano_venc = ano
        mes_venc = mes + 1

    vencimento = date(ano_venc, mes_venc, 20)
    feriados = feriados_nacionais_br(ano_venc) | (feriados or set())

    while vencimento.weekday() >= 5 or vencimento in feriados:
        vencimento -= timedelta(days=1)

    return vencimento


def competencia_para_texto(valor: date) -> str:
    return valor.strftime("%m/%Y")
