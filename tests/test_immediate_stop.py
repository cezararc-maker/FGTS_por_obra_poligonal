import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fgts_obra.app_final import AppFGTSFinal


class ImmediateStopTests(unittest.TestCase):
    @patch('fgts_obra.app_final.os._exit')
    def test_stops_only_when_lot_is_running(self, exit_process):
        idle = SimpleNamespace(_executando=False)
        AppFGTSFinal._parar_imediatamente(idle)
        exit_process.assert_not_called()

        running = SimpleNamespace(_executando=True)
        AppFGTSFinal._parar_imediatamente(running)
        exit_process.assert_called_once_with(130)


if __name__ == '__main__':
    unittest.main()
