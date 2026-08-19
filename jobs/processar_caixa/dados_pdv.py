"""Acesso aos movimentos de caixa armazenados no Firebird."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Iterator

import firebirdsql
import pandas as pd

from src.config import DatabaseConfig


CONSULTA_SANGRIAS = """
SELECT DATAMOVIMENTO, IDFILIAL, IDFUNCIONARIO, IDCX, IDFONTE AS IDPDV,
       SEQDIARIA, SEQMOV, HORA, DESCRICAO, VALOR
FROM MOVCAIXA
WHERE DATAMOV = ?
"""

CONSULTA_PAGAMENTOS = """
SELECT P.DESCRICAOPORTADOR, R.IDFILIAL, R.DATAEMISSAO, R.NUMERORECEBER,
       R.IDPORTADOR, R.IDVENDEDOR, R.VENCIMENTO, R.NUMEROSAIDA,
       R.DOCTOCLIENTE, R.VALOR, R.VALORPAGO, R.NUMEROCUPOMFISCAL,
       R.IDFUNCIONARIO, R.IDPDV, R.DA, R.IDCX, R.NSU, R.NUMCARTAO,
       R.CODIGOAUTORIZACAO, R.NSUSITEF
FROM RECEBER R
INNER JOIN PORTADOR P ON P.IDPORTADOR = R.IDPORTADOR
WHERE R.DATAEMISSAO = ?
"""


class CaixaRepository:
    def __init__(self, config: DatabaseConfig):
        self.config = config

    @contextmanager
    def _connection(self) -> Iterator[object]:
        connection = firebirdsql.connect(
            host=self.config.host, database=self.config.database,
            port=self.config.port, user=self.config.user,
            password=self.config.password, charset=self.config.charset,
        )
        try:
            yield connection
        finally:
            connection.close()

    def buscar_movimentos(self, data_movimento: date, caminho_consulta_vendas: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        if not caminho_consulta_vendas.is_file():
            raise FileNotFoundError(f"Consulta de vendas não encontrada: {caminho_consulta_vendas}")
        consulta_vendas = caminho_consulta_vendas.read_text(encoding="utf-8")
        with self._connection() as connection:
            vendas = self._consultar(connection, consulta_vendas)
            sangrias = self._consultar(connection, CONSULTA_SANGRIAS, (data_movimento,))
            pagamentos = self._consultar(connection, CONSULTA_PAGAMENTOS, (data_movimento,))
        return vendas, sangrias, pagamentos

    @staticmethod
    def _consultar(connection: object, sql: str, parametros: tuple = ()) -> pd.DataFrame:
        cursor = connection.cursor()
        try:
            if parametros:
                cursor.execute(sql, parametros)
            else:
                cursor.execute(sql)
            colunas = [descricao[0] for descricao in cursor.description]
            return pd.DataFrame(cursor.fetchall(), columns=colunas)
        finally:
            cursor.close()
