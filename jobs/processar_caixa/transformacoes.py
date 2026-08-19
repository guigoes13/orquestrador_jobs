"""Normalização dos dados de caixa antes do envio ao SharePoint."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd


FUSO_LOCAL = ZoneInfo("America/Sao_Paulo")


def sanitizar_textos(tabela: pd.DataFrame) -> pd.DataFrame:
    tabela = tabela.copy()

    for coluna in tabela.select_dtypes(include=["object"]).columns:
        tabela[coluna] = tabela[coluna].map(_sanitizar_texto)

    return tabela


def _sanitizar_texto(valor: Any) -> Any:
    if valor is None or pd.isna(valor):
        return ""

    if not isinstance(valor, str):
        return valor

    return " ".join(valor.replace('"', "").replace("'", "").split())


def data_hora_utc(data: Any, hora: Any = None) -> str | None:
    if data is None or pd.isna(data):
        return None
    try:
        instante = pd.Timestamp(data)
        dia = instante.date()
        horario = instante.time() if hora is None else _converter_hora(hora)
        local = datetime.combine(dia, horario, tzinfo=FUSO_LOCAL)

        return local.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError):
        return None


def _converter_hora(valor: Any) -> time:
    if valor is None or pd.isna(valor) or str(valor).strip() in {"", "A"}:
        return time()
    if isinstance(valor, time):
        return valor.replace(tzinfo=None)
    return time(*[int(parte) for parte in str(valor).split(":")])


def preparar_movimentos(vendas: pd.DataFrame, sangrias: pd.DataFrame,
                        pagamentos: pd.DataFrame, data_movimento: date) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:

    vendas, sangrias, pagamentos = map(sanitizar_textos, (vendas, sangrias, pagamentos))
    abertura = pd.to_datetime(vendas["DATAABERTURA"], errors="coerce")

    vendas = vendas[abertura.dt.date == data_movimento].copy()

    vendas["DATAHORA_ABERTURA"] = vendas.apply(
        lambda linha: data_hora_utc(linha["DATAABERTURA"], linha["HORAABERTURA"]), axis=1)

    vendas["DATAHORA_FECHAMENTO"] = vendas.apply(
        lambda linha: data_hora_utc(linha["DATAFECHAMENTO"], linha["HORAFECHAMENTO"]), axis=1)

    vendas["DA"] = vendas["DA"].map(data_hora_utc)

    sangrias["DATAHORA"] = sangrias.apply(
        lambda linha: data_hora_utc(linha["DATAMOVIMENTO"], linha["HORA"]), axis=1)

    pagamentos["DATAEMISSAO"] = pagamentos["DATAEMISSAO"].map(data_hora_utc)

    return vendas, sangrias, pagamentos
