from unittest import TestCase

from jobs.processar_produtos.produtos import criar_tabela


class CriarTabelaTests(TestCase):
    def test_normaliza_ids_de_lookup_retornados_como_texto(self):
        tabela = criar_tabela(
            [{"ID": "10", "FilialId": "2", "ProdutoId": "35"}],
            ["ID", "FilialId", "ProdutoId"],
        )

        self.assertEqual(10, tabela.iloc[0]["ID"])
        self.assertEqual(2, tabela.iloc[0]["FilialId"])
        self.assertEqual(35, tabela.iloc[0]["ProdutoId"])

    def test_valores_de_id_ausentes_nao_causam_erro(self):
        tabela = criar_tabela(
            [{"ID": "10", "FilialId": None}],
            ["ID", "FilialId"],
        )

        self.assertTrue(tabela["FilialId"].isna().all())
