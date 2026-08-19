"""Relatórios CSV do processar_produtos."""

from datetime import datetime
from pathlib import Path

import pandas as pd


def salvar_relatorios(diretorio_saida: Path, registro_produtos: pd.DataFrame,
                      produtos: pd.DataFrame, vendas: pd.DataFrame,
                      agora: datetime) -> tuple[Path, Path]:
    sufixo = agora.strftime("%Y-%m-%d %H_%M_%S.%f")
    caminho_produtos = diretorio_saida / f"PRODUTOS_{sufixo}.csv"
    caminho_resumo = diretorio_saida / f"RESUMOPDV_{sufixo}.csv"
    registro_produtos.to_csv(caminho_produtos, index=False)

    vendas_agrupadas = vendas.groupby("IDPRODUTOPDV", as_index=False)["QTDE"].sum().round(3)
    vendas_agrupadas.columns = ["IdProdutoPDV", "QTDE"]
    nomes = produtos[["IdProdutoPDV", "NomeProdutoPDV"]].rename(columns={"NomeProdutoPDV": "PRODUTO"})
    nomes.merge(vendas_agrupadas, how="inner", on="IdProdutoPDV").to_csv(caminho_resumo, index=False)
    return caminho_produtos, caminho_resumo
