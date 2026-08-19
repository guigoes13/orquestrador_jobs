"""Sincronização do cadastro de produtos."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from src.api_sharepoint import SharePointRepository

from .dados_pdv import PdvRepository


COLUNAS_PRODUTOS = ["ID", "NomeProdutoPDV", "PrecoVenda", "PrecoUnitario", "Data",
                   "UnidadePDV", "GrupoPDVId", "IdProdutoLojaId", "IdProdutoPDV",
                   "DataAlteracao", "FatorVenda"]
INVALID_NAME_CHARACTERS = "ЗБУГЙРйХА"


def limpar_nome_produto(nome: str) -> str:
    """Normaliza caracteres cirílicos encontrados em descrições legadas."""
    for caractere in INVALID_NAME_CHARACTERS:
        nome = nome.replace(caractere, "-")
    for sequencia in ("Ð‘", "Ð—", "Ð™", "Ðª", "Ð·Ð³", "Ð³"):
        nome = nome.replace(sequencia, "-")
    return nome


def criar_tabela(itens: list[dict[str, Any]], colunas: list[str]) -> pd.DataFrame:
    tabela = pd.DataFrame(
        [{coluna: item.get(coluna) for coluna in colunas} for item in itens],
        columns=colunas,
    )
    # O Microsoft Graph devolve IDs de lookup como texto. Normaliza todos os
    # identificadores para permitir comparacoes com os IDs inteiros do PDV e
    # do ConfigApp.ini.
    for coluna in (nome for nome in colunas if nome.casefold().endswith("id")):
        tabela[coluna] = pd.to_numeric(tabela[coluna], errors="coerce")
    return tabela


def _foi_alterado(valor_remoto: Any, valor_local: datetime | None) -> bool:
    if valor_local is None or pd.isna(valor_remoto):
        return False
    remoto = pd.to_datetime(valor_remoto, utc=True).tz_convert("America/Sao_Paulo").replace(microsecond=0)
    local = pd.to_datetime(valor_local).tz_localize("America/Sao_Paulo").replace(microsecond=0)
    return remoto != local


def sincronizar_produtos(
    pdv: PdvRepository,
    sharepoint: SharePointRepository,
    nome_lista: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    produtos_remotos = criar_tabela(sharepoint.get_items(nome_lista), COLUNAS_PRODUTOS)
    registros: list[dict[str, Any]] = []

    for numero_linha, linha in enumerate(pdv.buscar_produtos(), start=1):
        (id_produto, unidade, id_grupo, _subgrupo, nome, _promocao, custo,
         _custo_medio, preco_venda, _ultima_alteracao_preco, alterado_em,
         _balanca, ativo) = linha
        nome = limpar_nome_produto(nome)
        correspondentes = produtos_remotos[produtos_remotos["IdProdutoPDV"] == id_produto]
        operacao = "Identico"

        valores = {
            "Title": nome,
            "NomeProdutoPDV": nome,
            "PrecoVenda": round(preco_venda or 0, 3),
            "PrecoUnitario": round(custo or 0, 3),
            "UnidadePDV": unidade,
            "GrupoPDVId": id_grupo,
            "IdProdutoPDV": id_produto,
            "DataAlteracao": str(alterado_em),
            "Ativo": ativo,
        }
        if correspondentes.empty:
            sharepoint.create_item(nome_lista, valores)
            operacao = "Inserir"

        elif _foi_alterado(correspondentes.iloc[0].get("DataAlteracao"), alterado_em):
            valores["Data"] = str(pd.Timestamp.now())
            sharepoint.update_item(nome_lista, correspondentes.iloc[0]["ID"], valores)
            operacao = "Atualizar"

        registros.append({"IDLINHA": numero_linha, "IDPRODUTO": id_produto,
                          "DESCRICAO": nome, "OPERACAO": operacao})
    return produtos_remotos, pd.DataFrame(registros)
