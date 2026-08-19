from __future__ import annotations
from collections.abc import Callable
from decimal import Decimal
from typing import Any

import pandas as pd

from src.api_sharepoint import SharePointRepository


def nomes_listas(codigo_filial: int) -> tuple[str, str, str]:
    if codigo_filial not in range(1, 6):
        raise ValueError("O processamento de caixa aceita filiais de 1 a 5")

    return (
        f"VendasPorCaixa_{codigo_filial}",
        f"Sangria_Caixa_{codigo_filial}",
        f"Formas_Pagamento_{codigo_filial}"
    )


def sincronizar_movimentos(sharepoint: SharePointRepository, codigo_filial: int,
                           vendas: pd.DataFrame, sangrias: pd.DataFrame,
                           pagamentos: pd.DataFrame) -> dict[str, int]:

    lista_vendas, lista_sangrias, lista_pagamentos = nomes_listas(codigo_filial)

    return {
        "vendas": _inserir_novos(sharepoint, lista_vendas, vendas, "NUMERO_SAIDA", codigo_filial, _venda),
        "sangrias": _inserir_novos(sharepoint, lista_sangrias, sangrias, "SEQMOV", codigo_filial, _sangria),
        "pagamentos": _inserir_novos(sharepoint, lista_pagamentos, pagamentos, "NUMEROSAIDA", codigo_filial, _pagamento),
    }


def _normalizar_chave(valor: Any) -> str:

    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))

    return str(valor).strip()


def _inserir_novos(sharepoint: SharePointRepository, nome_lista: str,
                   tabela: pd.DataFrame, campo_chave: str, filial: int,
                   converter: Callable[[pd.Series, int], dict[str, Any]]) -> int:

    existentes = {
        _normalizar_chave(valor)
        for valor in sharepoint.get_field_values(nome_lista, campo_chave)
        if valor is not None
    }

    inseridos = 0
    for _, linha in tabela.iterrows():
        chave = _normalizar_chave(linha[campo_chave])

        if chave in existentes:
            continue

        valores = {campo: _valor_json(valor)
                   for campo, valor in converter(linha, filial).items()}

        sharepoint.create_item(nome_lista, valores)
        existentes.add(chave)
        inseridos += 1

    return inseridos


def _valor_json(valor: Any) -> Any:
    if valor is None or pd.isna(valor):
        return None
    if isinstance(valor, Decimal):
        return float(valor)
    return valor.item() if hasattr(valor, "item") else valor


def _venda(linha: pd.Series, filial: int) -> dict[str, Any]:
    return {
        "IDUNICO": f"{filial}_{linha['NUMERO_SAIDA']}",
        "NUMERO_SAIDA": linha["NUMERO_SAIDA"],
        "DATASAIDA": linha["DA"],
        "IDFUNCIONARIO": linha["IDFUNCIONARIO"],
        "Title": linha["NOMEFUNCIONARIO"],
        "IDCX": linha["IDCX"],
        "DATA": linha["DATAHORA_ABERTURA"],
        "DATAFECHAMENTO": linha["DATAHORA_FECHAMENTO"],
        "CAIXAFUNCIONARIO": linha["CAIXAFUNCIONARIO"],
        "STATUS": linha["STATUS"],
        "IDFILIAL": filial, "TIPOSAIDA": linha["TIPOSAIDA"],
        "IDPDV": linha["IDPDV"],
        "IDPRODUTO": linha["IDPRODUTO"],
        "IDSUBGRUPO": linha["IDSUBGRUPO"],
        "NOMESUBGRUPO": linha["NOMESUBGRUPO"],
        "DESCRICAOPRODUTO": linha["DESCRICAOPRODUTO"],
        "VENDA": linha["VENDA"],
    }


def _sangria(linha: pd.Series, filial: int) -> dict[str, Any]:
    return {
        "IDUNICO": f"{filial}_{linha['SEQMOV']}",
        "IDFILIAL": linha["IDFILIAL"],
        "IDFUNCIONARIO": linha["IDFUNCIONARIO"],
        "SEQMOV": linha["SEQMOV"],
        "IDCX": linha["IDCX"],
        "IDPDV": linha["IDPDV"],
        "DESCRICAO": linha["DESCRICAO"],
        "VALOR": linha["VALOR"],
        "DATAHORA": linha["DATAHORA"],
    }


def _pagamento(linha: pd.Series, filial: int) -> dict[str, Any]:
    return {
        "IDUNICO": f"{filial}_{linha['NUMEROSAIDA']}",
        "DATAEMISSAO": linha["DATAEMISSAO"],
        "IDFILIAL": linha["IDFILIAL"],
        "IDVENDEDOR": linha["IDFUNCIONARIO"],
        "NUMEROSAIDA": linha["NUMEROSAIDA"],
        "IDCX": linha["IDCX"],
        "NUMERORECEBER": linha["NUMERORECEBER"],
        "Title": linha["DESCRICAOPORTADOR"],
        "VALOR": linha["VALOR"],
    }
