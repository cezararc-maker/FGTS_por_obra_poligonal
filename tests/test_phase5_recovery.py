import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

from fgts_obra import phase5_flow
from fgts_obra import production_flow
from fgts_obra.portal_flow import PortalFlowError


class Phase5RecoveryTests(unittest.TestCase):
    def test_guia_sem_download_nao_e_tratada_como_concluida(self):
        with self.assertRaises(PortalFlowError):
            phase5_flow._salvar_guia_automatica(None, "10/2026", "900144852472", "123456789012-1")
        with self.assertRaises(PortalFlowError):
            production_flow._salvar_guia_direto(None, "10/2026", "900144852472", "123456789012-1")

    def test_numero_guia_normalizado(self):
        self.assertEqual(
            phase5_flow._normalizar_numero_guia(" 123456789012 – 1 "),
            "123456789012-1",
        )

    def test_reconhece_apenas_pdf_novo_baixado_pelo_chrome(self):
        with tempfile.TemporaryDirectory() as pasta:
            raiz = Path(pasta)
            downloads = raiz / "Downloads"
            downloads.mkdir()
            with patch("fgts_obra.phase5_flow.Path.home", return_value=raiz):
                antes = phase5_flow._estado_downloads_portal()
                pdf = downloads / "guia-do-portal.pdf"
                pdf.write_bytes(b"%PDF-1.4\nconteudo")
                self.assertEqual(phase5_flow._novo_pdf_do_portal(antes), pdf)


if __name__ == "__main__":
    unittest.main()
