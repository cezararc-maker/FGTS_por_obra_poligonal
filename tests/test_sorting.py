import unittest
from types import SimpleNamespace

from fgts_obra.app_final import AppFGTSFinal, _chave_ordenacao


class Table:
    def __init__(self):
        self.columns = ('situacao', 'linha', 'codigo', 'tipo', 'inscricao', 'servico', 'tag')
        self.rows = {
            '4': ('Pendente', '4', '10', 'CNO', '9003', 'Árvore', 'X'),
            '5': ('Pendente', '5', '2', 'CNO', '9001', 'Abacate', 'Y'),
            '6': ('Concluída', '6', '1', 'CNPJ', '0034', 'Zebra', 'Z'),
        }
        self.order = ['4', '5', '6']
        self.selected = {'4', '5'}
        self.titles = {}

    def __getitem__(self, key):
        assert key == 'columns'
        return self.columns

    def get_children(self):
        return tuple(self.order)

    def item(self, iid, key):
        assert key == 'values'
        return self.rows[iid]

    def move(self, iid, parent, index):
        self.order.remove(iid)
        self.order.insert(index, iid)

    def heading(self, key, **options):
        self.titles[key] = options['text']

    def selection(self):
        return tuple(self.selected)


class SortingTests(unittest.TestCase):
    def make_app(self):
        table = Table()
        items = [SimpleNamespace(linha=n) for n in (4, 5, 6)]
        titles = dict(zip(table.columns, ('Situação da guia', 'Linha', 'Código', 'Tipo', 'Inscrição', 'Serviço', 'TAG')))
        return SimpleNamespace(tabela=table, resultado=SimpleNamespace(itens=items),
                               _titulos_colunas=titles, _ordenacao_coluna=None,
                               _ordenacao_desc=False, _executando=False)

    def test_numeric_code_and_toggle_preserve_selection(self):
        app = self.make_app()
        AppFGTSFinal._ordenar_coluna(app, 'codigo')
        self.assertEqual(app.tabela.order, ['6', '5', '4'])
        self.assertEqual(app.tabela.titles['codigo'], 'Código ▲')
        self.assertEqual(app.tabela.selected, {'4', '5'})
        AppFGTSFinal._ordenar_coluna(app, 'codigo')
        self.assertEqual(app.tabela.order, ['4', '5', '6'])
        self.assertEqual(app.tabela.titles['codigo'], 'Código ▼')

    def test_selected_items_follow_visible_order(self):
        app = self.make_app()
        AppFGTSFinal._ordenar_coluna(app, 'codigo')
        self.assertEqual([item.linha for item in AppFGTSFinal._itens_selecionados(app)], [5, 4])

    def test_text_sort_ignores_accent(self):
        self.assertLess(_chave_ordenacao('servico', 'Árvore'), _chave_ordenacao('servico', 'Zebra'))


if __name__ == '__main__':
    unittest.main()
