"""Acesso do processar_produtos ao SharePoint."""

from __future__ import annotations

from typing import Any

import requests
from office365.runtime.auth.authentication_context import AuthenticationContext
from office365.sharepoint.client_context import ClientContext

from .config import SharePointConfig


class SharePointRepository:
    def __init__(self, config: SharePointConfig):
        self.config = config
        auth = AuthenticationContext(url=config.site_url)
        # A biblioteca configura a autenticação de forma preguiçosa; erros surgem
        # na primeira requisição e são propagados ao orquestrador com o traceback.
        auth.acquire_token_for_app(config.client_id, config.client_secret)
        self.context = ClientContext(config.site_url, auth)

        tenant = config.root_url.split("//", 1)[-1].split(".", 1)[0]
        response = requests.post(
            f"https://accounts.accesscontrol.windows.net/{config.tenant_id}/tokens/OAuth/2",
            data={
                "grant_type": "client_credentials",
                "resource": f"00000003-0000-0ff1-ce00-000000000000/{tenant}.sharepoint.com@{config.tenant_id}",
                "client_id": f"{config.client_id}@{config.tenant_id}",
                "client_secret": config.client_secret,
            },
            timeout=30,
        )
        response.raise_for_status()
        self.headers = {
            "Authorization": f"Bearer {response.json()['access_token']}",
            "Accept": "application/json;odata=verbose",
            "Content-Type": "application/json;odata=verbose",
        }

    def get_items(self, list_name: str) -> list[dict[str, Any]]:
        url = f"{self.config.site_url}/_api/web/lists/getbytitle('{list_name}')/items?$top=5000"
        response = requests.get(url, headers=self.headers, timeout=60)
        response.raise_for_status()
        return response.json()["d"]["results"]

    def create_item(self, list_name: str, values: dict[str, Any]) -> None:
        url = f"{self.config.site_url}/_api/web/lists/GetByTitle('{list_name}')/items"
        payload = {"__metadata": {"type": f"SP.Data.{list_name}ListItem"}, **values}
        response = requests.post(url, headers=self.headers, json=payload, timeout=30)
        response.raise_for_status()

    def update_item(self, list_name: str, item_id: int, values: dict[str, Any]) -> None:
        item = self.context.web.lists.get_by_title(list_name).get_item_by_id(int(item_id))
        for field, value in values.items():
            item.set_property(field, value)
        item.update()
        self.context.execute_query()
