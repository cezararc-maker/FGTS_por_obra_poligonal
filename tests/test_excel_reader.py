import tempfile
import unittest
from datetime import date
from pathlib import Path

from openpyxl import Workbook

from fgts_obra.excel_reader import ler_planilha, normalizar_inscricao


class TestExcelReader(unittest.TestCase):
    def test_cnpj_com_zero_inicial_e_reconstruido(self):
        inscricao, erro = normalizar_inscricao("CNPJ", 3492162000182)
        self.assertIsNone(erro)
        self.assertEqual(len(inscricao), 14)
        self.assertTrue(inscricao.startswith("0"))

    def test_cno_deve_ter_12_digitos(self):
        inscricao, erro = normalizar_inscricao("CNO", "900000000000")
        self.assertIsNone(erro)
        self.assertEqual(inscricao, "900000000000")

    def test_le_planilha_minima_valida(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "modelo.xlsx"
            wb = Workbook()
            ws = wb.active
            ws.title = "fgts_servicos (1)"
            ws["B1"] = date(2026, 8, 1)
            ws["E1"] = date(2026, 9, 18)

            cabecalhos = [
                "Codigo",
                "Tipo Inscrição",
                "Servico",
                "TAG",
                "Inscrição",
                "FGTS",
                "FGTS Aprendiz",
            ]
            for coluna, nome in enumerate(cabecalhos, start=1):
                ws.cell(3, coluna).value = nome

            ws.append([])
            ws.cell(4, 1).value = "001"
            ws.cell(4, 2).value = "CNO"
            ws.cell(4, 3).value = "OBRA TESTE"
            ws.cell(4, 4).value = "1 - OBRA TESTE"
            ws.cell(4, 5).value = "900000000000"
            ws.cell(4, 6).value = 100.0
            ws.cell(4, 7).value = 0.0
            wb.save(caminho)

            resultado = ler_planilha(caminho)
            self.assertTrue(resultado.valida)
            self.assertEqual(resultado.competencia, "08/2026")
            self.assertEqual(resultado.vencimento_calculado, date(2026, 9, 18))
            self.assertEqual(len(resultado.itens), 1)


if __name__ == "__main__":
    unittest.main()
