"""Transformação: lê data/raw, padroniza tipos e monta as tabelas processadas."""

import pandas as pd

from src.config import DIR_RAW
from src.indicadores import anualizar_taxa_diaria, indice_acumulado_d1


def ler_raw_sgs(nome: str) -> pd.DataFrame:
    """Lê data/raw/<nome>.csv e devolve as colunas data (datetime) e valor (float)."""
    # dtype=str: lê o bruto como texto, exatamente como foi gravado.
    bruto = pd.read_csv(DIR_RAW / f"{nome}.csv", dtype=str)

    df = pd.DataFrame(
        {
            # Formato explícito evita confundir dia e mês; as_unit("ns") fixa
            # a resolução, que o pandas 3 inferiria sozinho.
            "data": pd.to_datetime(bruto["data"], format="%d/%m/%Y").dt.as_unit("ns"),
            "valor": pd.to_numeric(bruto["valor"]),
        }
    )

    # O índice D-1 depende de "linha anterior = dia útil anterior".
    if df["data"].duplicated().any():
        raise ValueError(f"{nome}: há datas duplicadas no arquivo bruto.")
    if not df["data"].is_monotonic_increasing:
        raise ValueError(f"{nome}: as datas do arquivo bruto estão fora de ordem.")
    if df["valor"].isna().any():
        raise ValueError(f"{nome}: há valores vazios no arquivo bruto.")

    return df


def montar_diario() -> pd.DataFrame:
    """Tabela diária. Por enquanto só com o CDI; as outras séries entram depois."""
    cdi = ler_raw_sgs("cdi")

    return pd.DataFrame(
        {
            "data": cdi["data"],
            "cdi_taxa_ano": anualizar_taxa_diaria(cdi["valor"]),
            "cdi_indice": indice_acumulado_d1(cdi["valor"]),
        }
    )
