import unittest
from datetime import date

from fgts_obra.calendar_rules import calcular_vencimento_mensal


class TestCalendarRules(unittest.TestCase):
    def test_agosto_2026_antecipa_domingo(self):
        self.assertEqual(calcular_vencimento_mensal(2026, 8), date(2026, 9, 18))

    def test_mes_com_dia_20_util(self):
        self.assertEqual(calcular_vencimento_mensal(2026, 9), date(2026, 10, 20))

    def test_feriado_informado_antecipa(self):
        self.assertEqual(
            calcular_vencimento_mensal(2026, 9, {date(2026, 10, 20)}),
            date(2026, 10, 19),
        )


if __name__ == "__main__":
    unittest.main()
