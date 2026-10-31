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


def indice_acumulado(taxa_pct: pd.Series) -> pd.Series:
    """Índice acumulado (base 1,0) de uma variação % por período, INCLUINDO o
    próprio período: o valor de cada período já contém a variação dele.

    É a convenção do IPCA: a inflação de setembro acontece ao longo de
    setembro, então o índice de setembro já a inclui. Compare com
    indice_acumulado_d1, usado no CDI, em que a taxa de um dia só aparece
    no dia útil seguinte.
    """
    return (1 + taxa_pct / 100).cumprod()


def variacao_acumulada(indice: pd.Series, periodos: int) -> pd.Series:
    """Variação % do índice em relação ao valor de `periodos` posições antes.

    A série precisa ser contínua (sem períodos faltando) para que
    `periodos` posições signifiquem `periodos` meses.
    """
    return (indice / indice.shift(periodos) - 1) * 100


def anualizar_taxa_diaria(
    taxa_pct_dia: pd.Series, dias: int = DIAS_UTEIS_ANO
) -> pd.Series:
    """Converte uma taxa em % ao dia útil para % ao ano (base 252 dias úteis)."""
    return ((1 + taxa_pct_dia / 100) ** dias - 1) * 100


def base_100(indice: pd.Series) -> pd.Series:
    """Reescala um índice para valer 100 na primeira posição da série recebida."""
    return indice / indice.iloc[0] * 100


def variacao_mensal_d1(datas: pd.Series, indice: pd.Series) -> pd.Series:
    """Variação % de cada mês de um índice D-1, só para meses fechados.

    No índice D-1, o valor do primeiro dia útil de um mês inclui as taxas até
    o último dia útil do mês anterior. Logo, a razão entre o primeiro dia útil
    do mês seguinte e o primeiro dia útil do mês compõe exatamente as taxas
    registradas nos dias úteis do mês.

    O último mês da série fica de fora: sem nenhum dia do mês seguinte nos
    dados, ele não é considerado fechado.
    """
    primeiro_do_mes = indice.groupby(datas.dt.to_period("M")).first()
    return ((primeiro_do_mes.shift(-1) / primeiro_do_mes - 1) * 100).dropna()
