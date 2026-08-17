"""Sincronização do cadastro de produtos."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from .database import PdvRepository
from .sharepoint import SharePointRepository


PRODUCT_COLUMNS = ["ID", "NomeProdutoPDV", "PrecoVenda", "PrecoUnitario", "Data",
                   "UnidadePDV", "GrupoPDVId", "IdProdutoLojaId", "IdProdutoPDV",
                   "DataAlteracao", "FatorVenda"]
INVALID_NAME_CHARACTERS = "ЗБУГЙРйХА"


def clean_product_name(name: str) -> str:
    """Normaliza caracteres cirílicos encontrados em descrições legadas."""
    for character in INVALID_NAME_CHARACTERS:
        name = name.replace(character, "-")
    for sequence in ("Ð‘", "Ð—", "Ð™", "Ðª", "Ð·Ð³", "Ð³"):
        name = name.replace(sequence, "-")
    return name


def items_frame(items: list[dict[str, Any]], columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame([{column: item.get(column) for column in columns} for item in items], columns=columns)


class ProductSynchronizer:
    def __init__(self, pdv: PdvRepository, sharepoint: SharePointRepository, list_name: str):
        self.pdv = pdv
        self.sharepoint = sharepoint
        self.list_name = list_name

    def run(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        remote = items_frame(self.sharepoint.get_items(self.list_name), PRODUCT_COLUMNS)
        logs: list[dict[str, Any]] = []

        for line_number, row in enumerate(self.pdv.get_products(), start=1):
            (product_id, unit, group_id, _subgroup, name, _promotion, cost,
             _average_cost, sale_price, _last_price_change, changed_at, _scale, active) = row
            name = clean_product_name(name)
            matches = remote[remote["IdProdutoPDV"] == product_id]
            operation = "Identico"

            values = {
                "Title": name,
                "NomeProdutoPDV": name,
                "PrecoVenda": round(sale_price or 0, 3),
                "PrecoUnitario": round(cost or 0, 3),
                "UnidadePDV": unit,
                "GrupoPDVId": group_id,
                "IdProdutoPDV": product_id,
                "DataAlteracao": str(changed_at),
                "Ativo": active,
            }
            if matches.empty:
                self.sharepoint.create_item(self.list_name, values)
                operation = "Inserir"
            elif self._was_changed(matches.iloc[0].get("DataAlteracao"), changed_at):
                values["Data"] = str(pd.Timestamp.now())
                self.sharepoint.update_item(self.list_name, matches.iloc[0]["ID"], values)
                operation = "Atualizar"

            logs.append({"IDLINHA": line_number, "IDPRODUTO": product_id,
                         "DESCRICAO": name, "OPERACAO": operation})
        return remote, pd.DataFrame(logs)

    @staticmethod
    def _was_changed(remote_value: Any, local_value: datetime | None) -> bool:
        if local_value is None or pd.isna(remote_value):
            return False
        remote = pd.to_datetime(remote_value, utc=True).tz_convert("America/Sao_Paulo").replace(microsecond=0)
        local = pd.to_datetime(local_value).tz_localize("America/Sao_Paulo").replace(microsecond=0)
        return remote != local
