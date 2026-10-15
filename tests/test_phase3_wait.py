import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace
from fgts_obra import phase3_flow as flow


class WaitGradeTests(unittest.TestCase):
    def run_wait(self, loading_until=0, rows_until=0, enabled=True, total=2, loading_again=False):
        clock = [0.0]
        page = Mock()
        page.wait_for_timeout.side_effect = lambda ms: clock.__setitem__(0, clock[0] + ms / 1000)
        control = Mock()
        control.is_enabled.return_value = enabled
        def controls(_):
            if clock[0] < rows_until:
                raise flow.pf.PortalFlowError('linhas ainda ausentes')
            return control, [control]
        def loading(_):
            return [object()] if clock[0] < loading_until or (loading_again and 0.5 <= clock[0] < 1) else []
        with patch.object(flow.time, 'monotonic', side_effect=lambda: clock[0]), \
             patch.object(flow.pf, '_visiveis', side_effect=loading), \
             patch.object(flow, '_detectar_grade_resultados', return_value=total), \
             patch.object(flow, '_texto_pagina', return_value='Seleção de Débitos Competência de Apuração 09/2026 123456789012'), \
             patch.object(flow, '_checkboxes_grade', side_effect=controls):
            result = flow._aguardar_grade(page, '123456789012', '09/2026', timeout_ms=3000,
                                         campo_inscricao=SimpleNamespace(input_value=lambda: '123456789012'))
        control.click.assert_not_called()
        return result, clock[0]

    def test_waits_for_loading_even_with_existing_rows(self):
        self.assertEqual(self.run_wait(loading_until=1), (2, 1.75))

    def test_headers_alone_do_not_confirm_grid(self):
        self.assertEqual(self.run_wait(rows_until=1), (2, 1.75))

    def test_disabled_controls_timeout(self):
        with self.assertRaises(flow.pf.PortalFlowError):
            self.run_wait(enabled=False)

    def test_empty_results_timeout_without_selection(self):
        with self.assertRaises(flow.pf.PortalFlowError):
            self.run_wait(total=0)

    def test_grid_without_pagination_can_be_ready(self):
        self.assertEqual(self.run_wait(total=None), (None, 0.75))

    def test_new_loading_resets_stability(self):
        self.assertEqual(self.run_wait(loading_again=True), (2, 1.75))
