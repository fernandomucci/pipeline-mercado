"""Funções de cálculo puras: recebem séries do pandas e devolvem séries.

Não leem nem gravam arquivos, para poderem ser usadas pelo transform e pelo
dashboard e testadas isoladamente.
"""

import pandas as pd

# Convenção brasileira para taxas pós-fixadas: 252 dias úteis por ano.
DIAS_UTEIS_ANO = 252


def indice_acumulado_d1(taxa_pct: pd.Series) -> pd.Series:
    """Índice acumulado (base 1,0) de uma taxa em % por período, convenção D-1.

    A taxa registrada numa data remunera daquela data até a próxima data da
    série; por isso o valor de cada data inclui as taxas até a data anterior.

    A série precisa estar no calendário da própria taxa (ex.: dias úteis do
    CDI), ordenada e sem lacunas, ANTES de ser alinhada com outras séries.
    """
    fator = 1 + taxa_pct / 100
    return fator.shift(1, fill_value=1.0).cumprod()


def anualizar_taxa_diaria(
    taxa_pct_dia: pd.Series, dias: int = DIAS_UTEIS_ANO
) -> pd.Series:
    """Converte uma taxa em % ao dia útil para % ao ano (base 252 dias úteis)."""
    return ((1 + taxa_pct_dia / 100) ** dias - 1) * 100

def base_100(indice: pd.Series) -> pd.Series:
    """Reescala um índice para valer 100 na primeira posição da série recebida."""
    return indice / indice.iloc[0] * 100
