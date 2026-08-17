"""Acesso do processar_produtos ao Firebird."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from typing import Iterator

import firebirdsql
import pandas as pd

from .config import DatabaseConfig


PRODUCT_SQL = """
SELECT IDPRODUTO, UNIDADEMEDIDA, IDGRUPO, IDSUBGRUPO, DESCRICAOPRODUTO,
       PRECOPROMOCAO, CUSTO, CUSTOMEDIO, PRECOAVISTA, ULTIMADATAALTPRECO,
       CAST(DA AS timestamp) AS DATAALT, BALANCA,
       CASE ATIVO WHEN 'T' THEN 1 ELSE 0 END AS ATIVO
FROM PRODUTO
"""

SALES_SQL = """
SELECT IDPRODUTO, DATASAIDA, IDFILIAL, CAST(DA AS TIMESTAMP) AS DA,
       SEQUENCIA, NUMEROSAIDA, PUNIT, CUSTO, QTDE, PRECOPRODUTO, SUBTOTAL
FROM ITEMSAIDA
WHERE DATASAIDA = ?
ORDER BY IDPRODUTO, DATASAIDA
"""


class PdvRepository:
    def __init__(self, config: DatabaseConfig):
        self.config = config

    @contextmanager
    def _connection(self) -> Iterator[object]:
        connection = firebirdsql.connect(
            host=self.config.host,
            database=self.config.database,
            port=self.config.port,
            user=self.config.user,
            password=self.config.password,
            charset=self.config.charset,
        )
        try:
            yield connection
        finally:
            connection.close()

    def get_products(self) -> list[tuple]:
        with self._connection() as connection:
            cursor = connection.cursor()
            cursor.execute(PRODUCT_SQL)
            return cursor.fetchall()

    def get_sales(self, movement_date: date) -> pd.DataFrame:
        columns = ["IDPRODUTOPDV", "DATA", "SEQUENCIA", "NUMEROSAIDA",
                   "PRECOUNITARIO", "PRECOCUSTO", "QTDE", "PRECOVENDA", "SUBTOTAL"]
        with self._connection() as connection:
            cursor = connection.cursor()
            cursor.execute(SALES_SQL, (movement_date,))
            values = [(r[0], r[3], *r[4:]) for r in cursor.fetchall()]
        return pd.DataFrame(values, columns=columns)
