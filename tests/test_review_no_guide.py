import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fgts_obra import batch_state


class ReviewNoGuideTests(unittest.TestCase):
    def test_explicit_review_releases_only_uncertain_guide(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(
            batch_state, "_pasta_controle", return_value=Path(folder)
        ):
            args = ("09/2026", "CNO", "900153138674")
            batch_state.salvar_status(*args, status="CONFERIR_EMISSAO")
            batch_state.registrar_guia_nao_encontrada(*args)
            registro = batch_state.registro_item(*args)
            self.assertEqual(registro["status"], "LIBERADO_REEMISSAO")
            self.assertIn("não encontrou guia", registro["erro"])
            with self.assertRaises(ValueError):
                batch_state.registrar_guia_nao_encontrada(*args)

    def test_concluded_guide_cannot_be_released(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(
            batch_state, "_pasta_controle", return_value=Path(folder)
        ):
            args = ("09/2026", "CNO", "900153138674")
            batch_state.salvar_status(*args, status="CONCLUIDO")
            with self.assertRaises(ValueError):
                batch_state.registrar_guia_nao_encontrada(*args)
            self.assertEqual(batch_state.status_atual(*args), "CONCLUIDO")


if __name__ == "__main__":
    unittest.main()
