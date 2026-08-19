from unittest import TestCase
from unittest.mock import Mock

import pandas as pd

from jobs.processar_caixa.sincronizacao import _inserir_novos


class InserirNovosTests(TestCase):
    def test_consulta_somente_campo_chave_e_insere_apenas_novos(self):
        sharepoint = Mock()
        sharepoint.get_field_values.return_value = [100.0, None]
        tabela = pd.DataFrame([{"CHAVE": 100}, {"CHAVE": 200}])

        inseridos = _inserir_novos(
            sharepoint,
            "Lista",
            tabela,
            "CHAVE",
            1,
            lambda linha, filial: {
                "CHAVE": linha["CHAVE"],
                "FILIAL": filial,
            },
        )

        self.assertEqual(1, inseridos)
        sharepoint.get_field_values.assert_called_once_with("Lista", "CHAVE")
        sharepoint.create_item.assert_called_once_with(
            "Lista", {"CHAVE": 200, "FILIAL": 1}
        )
