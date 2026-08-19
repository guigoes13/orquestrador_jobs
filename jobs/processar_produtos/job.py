"""Fluxo principal do job processar_produtos."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.api_sharepoint import SharePointRepository
from src.config import load_config

from .dados_pdv import PdvRepository
from .inventario import COLUNAS_INVENTARIO, processar_inventario
from .produtos import criar_tabela, sincronizar_produtos
from .relatorios import salvar_relatorios


LOGGER = logging.getLogger(__name__)


def processar_produtos(caminho_configuracao: str | Path = "ConfigApp.ini") -> None:
    config = load_config(caminho_configuracao)
    agora = datetime.now()
    pdv = PdvRepository(config.database)
    sharepoint = SharePointRepository(config.sharepoint)

    LOGGER.info("Sincronizando produtos da filial %s", config.branch.name)
    produtos, registro_produtos = sincronizar_produtos(
        pdv, sharepoint, config.branch.product_list
    )

    inventario = criar_tabela(sharepoint.get_items("InventarioLoja"), COLUNAS_INVENTARIO)
    inventario = inventario[inventario["FilialId"] == config.branch.inventory_id]
    vendas = pdv.buscar_vendas(agora.date())
    if not vendas.empty:
        vendas["DATA"] = pd.to_datetime(vendas["DATA"])

    LOGGER.info("Processando %d itens de inventário", len(inventario))
    processar_inventario(sharepoint, inventario, produtos, vendas, agora)
    relatorio_produtos, relatorio_vendas = salvar_relatorios(
        config.output_dir, registro_produtos, produtos, vendas, agora
    )
    LOGGER.info("Relatórios gerados: %s e %s", relatorio_produtos.name, relatorio_vendas.name)
