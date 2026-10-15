import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from fgts_obra.app_final import AppFGTSFinal


class ImmediateStopTests(unittest.TestCase):
    def test_parada_mantem_janela_e_sinaliza_worker(self):
        evento = threading.Event()
        app = SimpleNamespace(
            _executando=True, _parar_agora=evento,
            btn_parar_agora=Mock(), _registrar=Mock(),
        )
        AppFGTSFinal._parar_imediatamente(app)
        self.assertTrue(evento.is_set())
        app.btn_parar_agora.configure.assert_called_once_with(state="disabled")
        app._registrar.assert_called_once()

    def test_parada_nao_faz_nada_sem_lote(self):
        evento = threading.Event()
        app = SimpleNamespace(_executando=False, _parar_agora=evento)
        AppFGTSFinal._parar_imediatamente(app)
        self.assertFalse(evento.is_set())


if __name__ == "__main__":
    unittest.main()
