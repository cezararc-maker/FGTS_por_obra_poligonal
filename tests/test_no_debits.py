import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fgts_obra import phase3_flow as flow, production_flow


class NoDebitsTests(unittest.TestCase):
    def test_empty_grid_is_recognized_without_waiting_full_timeout(self):
        clock = [0.0]
        page = Mock()
        page.wait_for_timeout.side_effect = lambda ms: clock.__setitem__(0, clock[0] + ms / 1000)
        body = 'Seleção de Débitos Competência de Apuração Nenhum item encontrado'
        with patch.object(flow.time, 'monotonic', side_effect=lambda: clock[0]), \
             patch.object(flow.pf, '_visiveis', return_value=[]), \
             patch.object(flow, '_detectar_grade_resultados', return_value=None), \
             patch.object(flow, '_texto_pagina', return_value=body), \
             patch.object(flow, '_checkboxes_grade') as checkboxes:
            with self.assertRaises(flow.SemDebitos):
                flow._aguardar_grade(page, '900158866078', '09/2026', campo_inscricao=SimpleNamespace(input_value=lambda: '900158866078'))
        self.assertLess(clock[0], 3)
        checkboxes.assert_not_called()

    def test_loading_overlay_prevents_premature_empty_result(self):
        clock = [0.0]
        page = Mock()
        page.wait_for_timeout.side_effect = lambda ms: clock.__setitem__(0, clock[0] + ms / 1000)
        body = 'Seleção de Débitos Competência de Apuração Nenhum item encontrado'
        with patch.object(flow.time, 'monotonic', side_effect=lambda: clock[0]), \
             patch.object(flow.pf, '_visiveis', side_effect=lambda _: [object()] if clock[0] < 2 else []), \
             patch.object(flow, '_detectar_grade_resultados', return_value=None), \
             patch.object(flow, '_texto_pagina', return_value=body):
            with self.assertRaises(flow.SemDebitos):
                flow._aguardar_grade(page, '900158866078', '09/2026', campo_inscricao=SimpleNamespace(input_value=lambda: '900158866078'))
        self.assertGreaterEqual(clock[0], 3)

    def test_resultado_vazio_nao_usa_inscricao_de_outra_pesquisa(self):
        clock = [0.0]
        page = Mock()
        page.wait_for_timeout.side_effect = lambda ms: clock.__setitem__(0, clock[0] + ms / 1000)
        with patch.object(flow.time, 'monotonic', side_effect=lambda: clock[0]), \
             patch.object(flow.pf, '_visiveis', return_value=[]), \
             patch.object(flow, '_detectar_grade_resultados', return_value=None), \
             patch.object(flow, '_texto_pagina', return_value='Seleção de Débitos Competência de Apuração Nenhum item encontrado'):
            with self.assertRaises(flow.pf.PortalFlowError) as erro:
                flow._aguardar_grade(page, '900158866078', '09/2026', timeout_ms=1500,
                                    campo_inscricao=SimpleNamespace(input_value=lambda: '900000000000'))
        self.assertNotIsInstance(erro.exception, flow.SemDebitos)

    @patch.object(production_flow, 'pasta_destino_item')
    @patch.object(production_flow, 'salvar_status')
    @patch.object(production_flow.p5, 'executar_fase5', side_effect=flow.SemDebitos('Não há débitos'))
    def test_no_debits_writes_status_without_creating_cno_folder(self, _, save, folder):
        item = SimpleNamespace(tipo_inscricao='CNO', inscricao='900158866078', tag='TESTE')
        with self.assertRaises(flow.SemDebitos):
            production_flow.executar_item_producao(
                Mock(), item=item, competencia='09/2026', vencimento=None,
                log=Mock(), indice=1, total=1,
            )
        folder.assert_not_called()
        self.assertEqual(save.call_args_list[-1].kwargs['status'], 'SEM_DEBITOS')


if __name__ == '__main__':
    unittest.main()
