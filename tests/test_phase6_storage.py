from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from fgts_obra.phase6_flow import _competencia_mmaaaa, gerar_zip_competencia, pasta_destino_item


class Phase6StorageTests(unittest.TestCase):
    def test_competencia_mmaaaa(self):
        self.assertEqual(_competencia_mmaaaa("08/2026"), "082026")
        self.assertEqual(_competencia_mmaaaa("1/2027"), "012027")

    def test_pasta_destino_usa_downloads_e_tag(self):
        with tempfile.TemporaryDirectory() as tmp, patch("pathlib.Path.home", return_value=Path(tmp)):
            pasta = pasta_destino_item("08/2026", "91-IMP. FEIRA CENTRAL TL -  900294970375", "900294970375")
            self.assertEqual(
                pasta,
                Path(tmp) / "Downloads" / "FGTS_por_obra_poligonal" / "08-2026" / "91-IMP. FEIRA CENTRAL TL - 900294970375",
            )
            self.assertTrue(pasta.exists())

    def test_zip_inclui_somente_subpastas_da_competencia(self):
        with tempfile.TemporaryDirectory() as tmp, patch("pathlib.Path.home", return_value=Path(tmp)):
            raiz = Path(tmp) / "Downloads"
            raiz.mkdir()
            (raiz / "arquivo_solto.pdf").write_bytes(b"fora")

            pasta_a = pasta_destino_item("08/2026", "89-OBRA A 9001", "9001")
            pasta_b = pasta_destino_item("08/2026", "90-OBRA B 9002", "9002")
            (pasta_a / "guia-a.pdf").write_bytes(b"A")
            (pasta_b / "guia-b.pdf").write_bytes(b"B")

            competencia = pasta_a.parent
            (competencia / "controle_lote.json").write_text("{}", encoding="utf-8")

            destino = gerar_zip_competencia("08/2026")
            self.assertEqual(destino.name, "Guias de FGTS por Obra 082026.zip")

            with zipfile.ZipFile(destino) as zf:
                nomes = set(zf.namelist())

            self.assertIn("89-OBRA A 9001/guia-a.pdf", nomes)
            self.assertIn("90-OBRA B 9002/guia-b.pdf", nomes)
            self.assertNotIn("arquivo_solto.pdf", nomes)
            self.assertNotIn("controle_lote.json", nomes)


if __name__ == "__main__":
    unittest.main()
