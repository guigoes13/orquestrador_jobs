"""Acesso às listas do SharePoint pela Microsoft Graph API."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import msal
import requests

from src.config import SharePointConfig


GRAPH_URL = "https://graph.microsoft.com/v1.0"
GRAPH_SCOPE = ["https://graph.microsoft.com/.default"]


class SharePointRepository:
    """Opera listas do SharePoint usando autenticação MSAL client credentials."""

    def __init__(self, config: SharePointConfig):
        self.config = config
        parsed_site = urlparse(config.site_url)
        self.site_host = parsed_site.netloc
        self.site_path = parsed_site.path.rstrip("/")
        self.session = requests.Session()
        self.msal_app = msal.ConfidentialClientApplication(
            client_id=config.client_id,
            client_credential=config.client_secret,
            authority=f"https://login.microsoftonline.com/{config.tenant_id}",
        )
        self._site_id: str | None = None
        self._list_ids: dict[str, str] = {}
        self._columns: dict[str, dict[str, dict[str, Any]]] = {}

    def _headers(self) -> dict[str, str]:
        token = self.msal_app.acquire_token_for_client(scopes=GRAPH_SCOPE)
        access_token = token.get("access_token")
        if not access_token:
            error = token.get("error_description") or token.get("error") or "erro desconhecido"
            raise RuntimeError(f"Falha ao autenticar no Microsoft Graph: {error}")
        return {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    def _request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        response = self.session.request(method, url, headers=self._headers(), timeout=60, **kwargs)
        response.raise_for_status()
        return response

    def _get_site_id(self) -> str:
        if self._site_id is None:
            site_reference = f"{self.site_host}:{self.site_path}" if self.site_path else self.site_host
            response = self._request("GET", f"{GRAPH_URL}/sites/{site_reference}")
            self._site_id = response.json()["id"]
        return self._site_id

    def _get_list_id(self, list_name: str) -> str:
        cache_key = list_name.casefold()
        if cache_key in self._list_ids:
            return self._list_ids[cache_key]

        url: str | None = f"{GRAPH_URL}/sites/{self._get_site_id()}/lists?$select=id,name,displayName"
        while url:
            data = self._request("GET", url).json()
            for item in data.get("value", []):
                names = (item.get("displayName", ""), item.get("name", ""))
                if any(name.casefold() == cache_key for name in names):
                    self._list_ids[cache_key] = item["id"]
                    return item["id"]
            url = data.get("@odata.nextLink")
        raise LookupError(f"Lista do SharePoint não encontrada: {list_name}")

    def _get_columns(self, list_name: str) -> dict[str, dict[str, Any]]:
        cache_key = list_name.casefold()
        if cache_key not in self._columns:
            list_id = self._get_list_id(list_name)
            url = f"{GRAPH_URL}/sites/{self._get_site_id()}/lists/{list_id}/columns"
            columns = self._request("GET", url).json().get("value", [])
            mapping: dict[str, dict[str, Any]] = {}
            for column in columns:
                for name in (column.get("name"), column.get("displayName")):
                    if name:
                        mapping[name.casefold()] = column
            self._columns[cache_key] = mapping
        return self._columns[cache_key]

    def _prepare_fields(self, list_name: str, values: dict[str, Any]) -> dict[str, Any]:
        """Converte nomes REST antigos, como FilialId, para nomes usados pelo Graph."""
        columns = self._get_columns(list_name)
        prepared: dict[str, Any] = {}
        for requested_name, value in values.items():
            column = columns.get(requested_name.casefold())
            graph_name = column.get("name") if column else requested_name

            if column is None and requested_name.casefold().endswith("id"):
                lookup_column = columns.get(requested_name[:-2].casefold())
                if lookup_column and "lookup" in lookup_column:
                    graph_name = f"{lookup_column['name']}LookupId"
            elif column and "lookup" in column:
                graph_name = f"{column['name']}LookupId"

            prepared[graph_name] = value
        return prepared

    @staticmethod
    def _legacy_fields(item: dict[str, Any]) -> dict[str, Any]:
        """Mantém os nomes esperados pela regra de negócio durante a migração."""
        fields = dict(item.get("fields", {}))
        for name, value in tuple(fields.items()):
            if name.endswith("LookupId"):
                fields[f"{name[:-8]}Id"] = value
        fields["ID"] = item["id"]
        fields["Id"] = item["id"]
        return fields

    def get_items(self, list_name: str) -> list[dict[str, Any]]:
        list_id = self._get_list_id(list_name)
        url: str | None = (
            f"{GRAPH_URL}/sites/{self._get_site_id()}/lists/{list_id}/items"
            "?$expand=fields&$top=999"
        )
        items: list[dict[str, Any]] = []
        while url:
            data = self._request("GET", url).json()
            items.extend(self._legacy_fields(item) for item in data.get("value", []))
            url = data.get("@odata.nextLink")
        return items

    def get_field_values(self, list_name: str, field_name: str) -> list[Any]:
        """Retorna somente os valores de uma coluna, percorrendo todas as paginas."""
        list_id = self._get_list_id(list_name)
        column = self._get_columns(list_name).get(field_name.casefold())
        graph_name = column.get("name") if column else field_name

        url: str | None = (
            f"{GRAPH_URL}/sites/{self._get_site_id()}/lists/{list_id}/items"
        )
        params: dict[str, str] | None = {
            "$select": "id",
            "$expand": f"fields($select={graph_name})",
            "$top": "999",
        }
        values: list[Any] = []

        while url:
            data = self._request("GET", url, params=params).json()
            values.extend(
                item.get("fields", {}).get(graph_name)
                for item in data.get("value", [])
            )
            url = data.get("@odata.nextLink")
            params = None

        return values

    def create_item(self, list_name: str, values: dict[str, Any]) -> None:
        list_id = self._get_list_id(list_name)
        url = f"{GRAPH_URL}/sites/{self._get_site_id()}/lists/{list_id}/items"
        self._request("POST", url, json={"fields": self._prepare_fields(list_name, values)})

    def update_item(self, list_name: str, item_id: int | str, values: dict[str, Any]) -> None:
        list_id = self._get_list_id(list_name)
        url = f"{GRAPH_URL}/sites/{self._get_site_id()}/lists/{list_id}/items/{item_id}/fields"
        self._request("PATCH", url, json=self._prepare_fields(list_name, values))
