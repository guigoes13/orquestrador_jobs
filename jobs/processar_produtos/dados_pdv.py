"""Acesso do processar_produtos ao Firebird."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from typing import Iterator

import firebirdsql
import pandas as pd

from src.config import DatabaseConfig


CONSULTA_PRODUTOS = """
SELECT IDPRODUTO, UNIDADEMEDIDA, IDGRUPO, IDSUBGRUPO, DESCRICAOPRODUTO,
       PRECOPROMOCAO, CUSTO, CUSTOMEDIO, PRECOAVISTA, ULTIMADATAALTPRECO,
       CAST(DA AS timestamp) AS DATAALT, BALANCA,
       CASE ATIVO WHEN 'T' THEN 1 ELSE 0 END AS ATIVO
FROM PRODUTO
"""

CONSULTA_VENDAS = """
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

    def buscar_produtos(self) -> list[tuple]:
        with self._connection() as connection:
            cursor = connection.cursor()
            cursor.execute(CONSULTA_PRODUTOS)
            return cursor.fetchall()

    def buscar_vendas(self, data_movimento: date) -> pd.DataFrame:
        colunas = ["IDPRODUTOPDV", "DATA", "SEQUENCIA", "NUMEROSAIDA",
                   "PRECOUNITARIO", "PRECOCUSTO", "QTDE", "PRECOVENDA", "SUBTOTAL"]
        with self._connection() as connection:
            cursor = connection.cursor()
            cursor.execute(CONSULTA_VENDAS, (data_movimento,))
            valores = [(linha[0], linha[3], *linha[4:]) for linha in cursor.fetchall()]
        return pd.DataFrame(valores, columns=colunas)
