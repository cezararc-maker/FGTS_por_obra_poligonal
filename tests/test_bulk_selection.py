import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fgts_obra.app_final import AppFGTSFinal


class BulkSelectionTests(unittest.TestCase):
    def make_app(self):
        items = [SimpleNamespace(linha=n, tipo_inscricao='CNO', inscricao=str(n)) for n in range(4, 9)]
        tabela = Mock()
        tabela.selection.return_value = ('4',)
        tabela.exists.return_value = True
        app = SimpleNamespace(_executando=False, resultado=SimpleNamespace(
            valida=True, competencia='09/2026', itens=items), tabela=tabela,
            status_var=Mock(), _iniciar_lote=Mock())
        return app

    @patch('fgts_obra.app_final.carregar_controle')
    def test_all_selects_only_never_processed(self, load):
        app = self.make_app()
        load.return_value = {
            '09/2026|CNO|4': {'status': 'CONCLUIDO'},
            '09/2026|CNO|5': {'status': 'ERRO'},
            '09/2026|CNO|6': {'status': 'GUIA_RECUPERADA'},
        }
        count = AppFGTSFinal._selecionar_pendentes(app)
        self.assertEqual(count, 2)
        app.tabela.selection_set.assert_called_once_with('7', '8')
        app._iniciar_lote.assert_not_called()

    def test_bulk_still_uses_existing_confirmation_flow(self):
        app = self.make_app()
        app._selecionar_pendentes = Mock(return_value=2)
        AppFGTSFinal._gerar_todas_pendentes(app)
        app._iniciar_lote.assert_called_once_with()

    def test_bulk_does_not_run_when_nothing_eligible(self):
        app = self.make_app()
        app._selecionar_pendentes = Mock(return_value=0)
        AppFGTSFinal._gerar_todas_pendentes(app)
        app._iniciar_lote.assert_not_called()


if __name__ == '__main__':
    unittest.main()
