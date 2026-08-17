"""Fluxo principal do job processar_produtos."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

from .config import load_config
from .database import PdvRepository
from .inventory import INVENTORY_COLUMNS, InventoryProcessor
from .products import ProductSynchronizer, items_frame
from .reports import save_reports
from .sharepoint import SharePointRepository


LOGGER = logging.getLogger(__name__)


def run(config_path: str | Path = "ConfigApp.ini") -> None:
    config = load_config(config_path)
    now = datetime.now()
    pdv = PdvRepository(config.database)
    sharepoint = SharePointRepository(config.sharepoint)

    LOGGER.info("Sincronizando produtos da filial %s", config.branch.name)
    products, product_log = ProductSynchronizer(
        pdv, sharepoint, config.branch.product_list
    ).run()

    inventory = items_frame(sharepoint.get_items("InventarioLoja"), INVENTORY_COLUMNS)
    inventory = inventory[inventory["FilialId"] == config.branch.inventory_id]
    sales = pdv.get_sales(now.date())
    if not sales.empty:
        sales["DATA"] = pd.to_datetime(sales["DATA"])

    LOGGER.info("Processando %d itens de inventário", len(inventory))
    InventoryProcessor(sharepoint).run(inventory, products, sales, now)
    product_report, sales_report = save_reports(
        config.output_dir, product_log, products, sales, now
    )
    LOGGER.info("Relatórios gerados: %s e %s", product_report.name, sales_report.name)
