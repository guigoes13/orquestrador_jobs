"""Inventário e vendas por turno do processar_produtos."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Any

import pandas as pd

from .sharepoint import SharePointRepository


INVENTORY_COLUMNS = [
    "ID", "Data", "EstoqueAtual", "EntradaEstoqueManha", "EstoqueTarde",
    "EntradaEstoqueTarde", "FilialId", "ProdutoId", "EstoqueFinalManha",
    "EstoqueFinalTarde", "DataInicioManha", "DataFimManha", "DataInicioTarde",
    "DataFimTarde", "QTVendasManha", "QTVendasTarde", "QTVendasManhaPeriodo",
    "QTVendasTardePeriodo",
]


@dataclass(frozen=True)
class Periods:
    morning_start: datetime | None
    morning_end: datetime | None
    afternoon_start: datetime | None
    afternoon_end: datetime | None
    morning_window_start: datetime
    morning_window_end: datetime
    afternoon_window_start: datetime
    afternoon_window_end: datetime
    automatic_morning_end: bool
    automatic_afternoon_end: bool


def _local_datetime(value: Any) -> datetime | None:
    if value is None or pd.isna(value):
        return None
    return pd.to_datetime(value, utc=True).tz_convert("America/Sao_Paulo").tz_localize(None).to_pydatetime()


def define_periods(row: pd.Series, now: datetime) -> Periods:
    morning_start = _local_datetime(row["DataInicioManha"])
    morning_end = _local_datetime(row["DataFimManha"])
    afternoon_start = _local_datetime(row["DataInicioTarde"])
    afternoon_end = _local_datetime(row["DataFimTarde"])
    day = (morning_start or afternoon_start or now).date()

    automatic_morning = morning_start is not None and morning_end is None and afternoon_start is not None
    if automatic_morning:
        morning_end = afternoon_start - timedelta(seconds=1)
    automatic_afternoon = afternoon_start is not None and afternoon_end is None
    if automatic_afternoon:
        afternoon_end = datetime.combine(day, time(22, 30))

    return Periods(morning_start, morning_end, afternoon_start, afternoon_end,
                   datetime.combine(day, time(5)), datetime.combine(day, time(13, 30)),
                   datetime.combine(day, time(13, 30)), datetime.combine(day, time(22, 30)),
                   automatic_morning, automatic_afternoon)


class InventoryProcessor:
    def __init__(self, sharepoint: SharePointRepository):
        self.sharepoint = sharepoint

    def run(self, inventory: pd.DataFrame, products: pd.DataFrame,
            sales: pd.DataFrame, now: datetime) -> None:
        for _, row in inventory.iterrows():
            linked_products = products[products["IdProdutoLojaId"] == row["ProdutoId"]]
            if linked_products.empty:
                continue
            periods = define_periods(row, now)
            totals = self._sales_totals(linked_products, sales, periods)

            final_morning = row["EstoqueFinalManha"]
            if now.time() >= time(12) and periods.automatic_morning_end and row["EstoqueAtual"] > 0:
                final_morning = row["EstoqueAtual"] + row["EntradaEstoqueManha"] - totals["QTVendasManha"]
            final_afternoon = row["EstoqueFinalTarde"]
            if now.time() >= time(20) and periods.automatic_afternoon_end and row["EstoqueTarde"] > 0:
                final_afternoon = row["EstoqueTarde"] + row["EntradaEstoqueTarde"] - totals["QTVendasTarde"]

            values = {**totals, "EstoqueFinalManha": final_morning,
                      "EstoqueFinalTarde": final_afternoon}
            # O SharePoint armazena UTC; o sistema legado compensa o fuso com +3 horas.
            if periods.automatic_morning_end and periods.morning_end:
                values["DataFimManha"] = (periods.morning_end + timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
            if periods.automatic_afternoon_end and periods.afternoon_end:
                values["DataFimTarde"] = (periods.afternoon_end + timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
            self.sharepoint.update_item("InventarioLoja", row["ID"], values)

    @staticmethod
    def _sales_totals(products: pd.DataFrame, sales: pd.DataFrame, periods: Periods) -> dict[str, float]:
        totals = {"QTVendasManha": 0.0, "QTVendasTarde": 0.0,
                  "QTVendasManhaPeriodo": 0.0, "QTVendasTardePeriodo": 0.0}
        mappings = [
            ("QTVendasManha", periods.morning_start, periods.morning_end),
            ("QTVendasTarde", periods.afternoon_start, periods.afternoon_end),
            ("QTVendasManhaPeriodo", periods.morning_window_start, periods.morning_window_end),
            ("QTVendasTardePeriodo", periods.afternoon_window_start, periods.afternoon_window_end),
        ]
        for _, product in products.iterrows():
            factor = product.get("FatorVenda")
            factor = factor if pd.notna(factor) and factor != 0 else 1
            product_sales = sales[sales["IDPRODUTOPDV"] == product["IdProdutoPDV"]]
            for field, start, end in mappings:
                if start is not None and end is not None:
                    quantity = product_sales.loc[product_sales["DATA"].between(start, end), "QTDE"].sum()
                    totals[field] += round(quantity / factor, 0)
        return totals
