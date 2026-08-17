"""Relatórios CSV do processar_produtos."""

from datetime import datetime
from pathlib import Path

import pandas as pd


def save_reports(output_dir: Path, product_log: pd.DataFrame,
                 products: pd.DataFrame, sales: pd.DataFrame, now: datetime) -> tuple[Path, Path]:
    suffix = now.strftime("%Y-%m-%d %H_%M_%S.%f")
    product_path = output_dir / f"PRODUTOS_{suffix}.csv"
    summary_path = output_dir / f"RESUMOPDV_{suffix}.csv"
    product_log.to_csv(product_path, index=False)

    grouped = sales.groupby("IDPRODUTOPDV", as_index=False)["QTDE"].sum().round(3)
    grouped.columns = ["IdProdutoPDV", "QTDE"]
    names = products[["IdProdutoPDV", "NomeProdutoPDV"]].rename(columns={"NomeProdutoPDV": "PRODUTO"})
    names.merge(grouped, how="inner", on="IdProdutoPDV").to_csv(summary_path, index=False)
    return product_path, summary_path
