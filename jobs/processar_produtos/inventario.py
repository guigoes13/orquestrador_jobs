"""Inventário e vendas por turno do processar_produtos."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Any

import pandas as pd

from src.api_sharepoint import SharePointRepository


COLUNAS_INVENTARIO = [
    "ID", "Data", "EstoqueAtual", "EntradaEstoqueManha", "EstoqueTarde",
    "EntradaEstoqueTarde", "FilialId", "ProdutoId", "EstoqueFinalManha",
    "EstoqueFinalTarde", "DataInicioManha", "DataFimManha", "DataInicioTarde",
    "DataFimTarde", "QTVendasManha", "QTVendasTarde", "QTVendasManhaPeriodo",
    "QTVendasTardePeriodo",
]


@dataclass(frozen=True)
class Periodos:
    inicio_manha: datetime | None
    fim_manha: datetime | None
    inicio_tarde: datetime | None
    fim_tarde: datetime | None
    inicio_intervalo_manha: datetime
    fim_intervalo_manha: datetime
    inicio_intervalo_tarde: datetime
    fim_intervalo_tarde: datetime
    fim_manha_automatico: bool
    fim_tarde_automatico: bool


def _data_hora_local(valor: Any) -> datetime | None:
    if valor is None or pd.isna(valor):
        return None
    return pd.to_datetime(valor, utc=True).tz_convert("America/Sao_Paulo").tz_localize(None).to_pydatetime()


def definir_periodos(linha: pd.Series, agora: datetime) -> Periodos:
    inicio_manha = _data_hora_local(linha["DataInicioManha"])
    fim_manha = _data_hora_local(linha["DataFimManha"])
    inicio_tarde = _data_hora_local(linha["DataInicioTarde"])
    fim_tarde = _data_hora_local(linha["DataFimTarde"])
    dia = (inicio_manha or inicio_tarde or agora).date()

    fim_manha_automatico = inicio_manha is not None and fim_manha is None and inicio_tarde is not None
    if fim_manha_automatico:
        fim_manha = inicio_tarde - timedelta(seconds=1)
    fim_tarde_automatico = inicio_tarde is not None and fim_tarde is None
    if fim_tarde_automatico:
        fim_tarde = datetime.combine(dia, time(22, 30))

    return Periodos(inicio_manha, fim_manha, inicio_tarde, fim_tarde,
                    datetime.combine(dia, time(5)), datetime.combine(dia, time(13, 30)),
                    datetime.combine(dia, time(13, 30)), datetime.combine(dia, time(22, 30)),
                    fim_manha_automatico, fim_tarde_automatico)


def _calcular_totais_vendas(
    produtos: pd.DataFrame, vendas: pd.DataFrame, periodos: Periodos
) -> dict[str, float]:
    totais = {"QTVendasManha": 0.0, "QTVendasTarde": 0.0,
              "QTVendasManhaPeriodo": 0.0, "QTVendasTardePeriodo": 0.0}
    intervalos = [
        ("QTVendasManha", periodos.inicio_manha, periodos.fim_manha),
        ("QTVendasTarde", periodos.inicio_tarde, periodos.fim_tarde),
        ("QTVendasManhaPeriodo", periodos.inicio_intervalo_manha, periodos.fim_intervalo_manha),
        ("QTVendasTardePeriodo", periodos.inicio_intervalo_tarde, periodos.fim_intervalo_tarde),
    ]
    for _, produto in produtos.iterrows():
        fator = produto.get("FatorVenda")
        fator = fator if pd.notna(fator) and fator != 0 else 1
        vendas_produto = vendas[vendas["IDPRODUTOPDV"] == produto["IdProdutoPDV"]]
        for campo, inicio, fim in intervalos:
            if inicio is not None and fim is not None:
                quantidade = vendas_produto.loc[vendas_produto["DATA"].between(inicio, fim), "QTDE"].sum()
                totais[campo] += round(quantidade / fator, 0)
    return totais


def processar_inventario(
    sharepoint: SharePointRepository,
    inventario: pd.DataFrame,
    produtos: pd.DataFrame,
    vendas: pd.DataFrame,
    agora: datetime,
) -> None:
    for _, linha in inventario.iterrows():
        produtos_vinculados = produtos[produtos["IdProdutoLojaId"] == linha["ProdutoId"]]
        if produtos_vinculados.empty:
            continue
        periodos = definir_periodos(linha, agora)
        totais = _calcular_totais_vendas(produtos_vinculados, vendas, periodos)

        estoque_final_manha = linha["EstoqueFinalManha"]
        if agora.time() >= time(12) and periodos.fim_manha_automatico and linha["EstoqueAtual"] > 0:
            estoque_final_manha = linha["EstoqueAtual"] + linha["EntradaEstoqueManha"] - totais["QTVendasManha"]
        estoque_final_tarde = linha["EstoqueFinalTarde"]
        if agora.time() >= time(20) and periodos.fim_tarde_automatico and linha["EstoqueTarde"] > 0:
            estoque_final_tarde = linha["EstoqueTarde"] + linha["EntradaEstoqueTarde"] - totais["QTVendasTarde"]

        valores = {**totais, "EstoqueFinalManha": estoque_final_manha,
                   "EstoqueFinalTarde": estoque_final_tarde}
        # O SharePoint armazena UTC; o sistema legado compensa o fuso com +3 horas.
        if periodos.fim_manha_automatico and periodos.fim_manha:
            valores["DataFimManha"] = (periodos.fim_manha + timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
        if periodos.fim_tarde_automatico and periodos.fim_tarde:
            valores["DataFimTarde"] = (periodos.fim_tarde + timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
        sharepoint.update_item("InventarioLoja", linha["ID"], valores)
