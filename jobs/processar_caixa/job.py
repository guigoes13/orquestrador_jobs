"""Fluxo principal do job processar_caixa."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from src.api_sharepoint import SharePointRepository
from src.config import load_config

from .dados_pdv import CaixaRepository
from .sincronizacao import sincronizar_movimentos
from .transformacoes import preparar_movimentos


LOGGER = logging.getLogger(__name__)


def processar_caixa(caminho_configuracao: str | Path = "ConfigApp.ini") -> None:

    caminho_configuracao = Path(caminho_configuracao).resolve()
    config = load_config(caminho_configuracao)
    data_movimento = datetime.now().date()
    pdv = CaixaRepository(config.database)

    sharepoint = SharePointRepository(config.sharepoint)

    vendas, sangrias, pagamentos = pdv.buscar_movimentos(
        data_movimento, caminho_configuracao.parent / "queryCaixa.sql")

    vendas, sangrias, pagamentos = preparar_movimentos(
        vendas, sangrias, pagamentos, data_movimento)

    quantidades = sincronizar_movimentos(
        sharepoint, config.branch.id, vendas, sangrias, pagamentos)

    LOGGER.info(
        "Caixa sincronizado: %d vendas, %d sangrias e %d pagamentos inseridos",
        quantidades["vendas"], quantidades["sangrias"], quantidades["pagamentos"],
    )
