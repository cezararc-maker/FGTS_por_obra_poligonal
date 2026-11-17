import unittest

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


if __name__ == "__main__":
    unittest.main()
