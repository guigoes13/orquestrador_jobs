from unittest import TestCase
from unittest.mock import Mock, call

from src.api_sharepoint.sharepoint import GRAPH_URL, SharePointRepository


class SharePointRepositoryTests(TestCase):
    def test_get_field_values_selects_only_requested_field_and_follows_paging(self):
        repository = SharePointRepository.__new__(SharePointRepository)
        repository._get_list_id = Mock(return_value="list-id")
        repository._get_site_id = Mock(return_value="site-id")
        repository._get_columns = Mock(return_value={
            "numero_saida": {"name": "NUMERO_x005f_SAIDA"}
        })

        first_response = Mock()
        first_response.json.return_value = {
            "value": [
                {"id": "1", "fields": {"NUMERO_x005f_SAIDA": 10}},
                {"id": "2", "fields": {"NUMERO_x005f_SAIDA": None}},
            ],
            "@odata.nextLink": "https://graph.microsoft.com/next-page",
        }
        second_response = Mock()
        second_response.json.return_value = {
            "value": [{"id": "3", "fields": {"NUMERO_x005f_SAIDA": 30}}]
        }
        repository._request = Mock(side_effect=[first_response, second_response])

        values = repository.get_field_values("Vendas", "NUMERO_SAIDA")

        self.assertEqual([10, None, 30], values)
        items_url = f"{GRAPH_URL}/sites/site-id/lists/list-id/items"
        self.assertEqual(
            [
                call("GET", items_url, params={
                    "$select": "id",
                    "$expand": "fields($select=NUMERO_x005f_SAIDA)",
                    "$top": "999",
                }),
                call("GET", "https://graph.microsoft.com/next-page", params=None),
            ],
            repository._request.call_args_list,
        )
