"""Carga: grava as tabelas tratadas em data/processed."""

from pathlib import Path

import pandas as pd


def salvar_csv(df: pd.DataFrame, caminho: Path) -> None:
    """Grava `df` em CSV, com datas no formato AAAA-MM-DD e sem a coluna de índice.

    Colunas de período (ex.: mês) são gravadas no formato próprio do período
    (2026-09), e não como data: o date_format do to_csv também se aplicaria
    a elas e as transformaria num dia (2026-09-30).
    """
    colunas_periodo = [c for c in df.columns if isinstance(df[c].dtype, pd.PeriodDtype)]
    df = df.assign(**{c: df[c].astype(str) for c in colunas_periodo})

    caminho.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(caminho, index=False, date_format="%Y-%m-%d")
    print(f"{caminho.name}: {len(df)} linhas -> {caminho}")