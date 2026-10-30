"""Carga: grava as tabelas tratadas em data/processed."""

from pathlib import Path

import pandas as pd


def salvar_csv(df: pd.DataFrame, caminho: Path) -> None:
    """Grava `df` em CSV, com datas no formato AAAA-MM-DD e sem a coluna de índice."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(caminho, index=False, date_format="%Y-%m-%d")
    print(f"{caminho.name}: {len(df)} linhas -> {caminho}")
