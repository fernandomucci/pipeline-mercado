"""Validação: confere os resultados do pipeline contra valores oficiais."""

import pandas as pd

from src.config import (
    ARQUIVO_DIARIO,
    ARQUIVO_MENSAL,
    DATA_INICIO_EXTRACAO,
    SERIE_VALIDACAO_CDI_MES,
)
from src.extract import baixar_serie_sgs, data_fim_padrao
from src.indicadores import variacao_mensal_d1

# Meia unidade da 2ª casa decimal: o maior erro de um valor arredondado
# para 2 casas.
MEIA_UNIDADE_2_CASAS = 0.005

# Só absorve a imprecisão de ponto flutuante nas comparações.
FOLGA_FLOAT = 1e-9

# IPCA acumulado em 12 meses, valores oficiais com 2 casas decimais.
# Fonte: IBGE. Conferidos em 31/10/2026.
IPCA_12M_IBGE = {
    "2021-12": 10.06,
    "2022-12": 5.79,
    "2023-12": 4.62,
    "2024-12": 4.83,
    "2025-12": 4.26,
    "2026-09": 4.58,
}


# --- CDI -----------------------------------------------------------------------


def validar_cdi_mensal(diario: pd.DataFrame) -> None:
    """Compara o CDI mensal do índice D-1 com a série 4391 do SGS (meses fechados).

    Tolerância: 0,005 p.p. O cálculo usa a série diária com 6 casas, e só a
    4391 vem arredondada para 2 casas.

    Levanta ValueError se algum mês ficar fora da tolerância.
    """
    # Só as datas em que o CDI existe de fato: a taxa ao ano nunca é
    # preenchida, então ela marca as datas reais da série 12. Isso deixa de
    # fora o fim vazio e, quando o Ibovespa entrar, datas só da bolsa.
    cdi = diario.dropna(subset=["cdi_taxa_ano"])
    calculado = variacao_mensal_d1(cdi["data"], cdi["cdi_indice"])

    bruto = baixar_serie_sgs(
        SERIE_VALIDACAO_CDI_MES, DATA_INICIO_EXTRACAO, data_fim_padrao()
    )
    meses = pd.to_datetime(bruto["data"], format="%d/%m/%Y").dt.to_period("M")
    referencia = pd.Series(
        pd.to_numeric(bruto["valor"]).to_numpy(),
        index=pd.PeriodIndex(meses),
    )

    # Alinha pelo mês e descarta o que não existe dos dois lados: o mês em
    # andamento (parcial na 4391) não tem valor calculado e sai aqui.
    comparacao = pd.DataFrame(
        {"calculado": calculado, "sgs_4391": referencia}
    ).dropna()

    if comparacao.empty:
        raise ValueError("Nenhum mês fechado em comum entre o cálculo e a 4391.")

    comparacao = comparacao.assign(
        diferenca=(comparacao["calculado"] - comparacao["sgs_4391"]).abs()
    )
    fora = comparacao[comparacao["diferenca"] > MEIA_UNIDADE_2_CASAS + FOLGA_FLOAT]

    print(
        f"Validação CDI x SGS {SERIE_VALIDACAO_CDI_MES}: "
        f"{len(comparacao)} meses fechados "
        f"({comparacao.index[0]} a {comparacao.index[-1]}), "
        f"{len(comparacao) - len(fora)} dentro da tolerância; "
        f"maior diferença {comparacao['diferenca'].max():.4f} p.p. "
        f"em {comparacao['diferenca'].idxmax()}"
    )

    if not fora.empty:
        raise ValueError(
            "CDI mensal fora da tolerância em relação à 4391:\n"
            + fora.round(4).to_string()
        )


# --- IPCA ----------------------------------------------------------------------


def tolerancia_acumulado(taxas_mensais_pct: pd.Series) -> float:
    """Maior diferença que o arredondamento pode causar num acumulado.

    Cada taxa mensal publicada com 2 casas tem erro de até 0,005 p.p. No
    acumulado, o erro de um mês pesa (produto dos fatores / fator do mês).
    Soma-se o pior caso de todos os meses da janela e mais 0,005 do
    arredondamento do próprio valor oficial.
    """
    fatores = 1 + taxas_mensais_pct / 100
    produto = fatores.prod()
    return MEIA_UNIDADE_2_CASAS * (produto / fatores).sum() + MEIA_UNIDADE_2_CASAS


def validar_ipca_12m(mensal: pd.DataFrame) -> None:
    """Compara o IPCA em 12 meses com os valores oficiais do IBGE.

    Tolerância calculada para cada mês pelo pior caso do arredondamento
    (ver tolerancia_acumulado). Levanta ValueError se algum mês de referência
    faltar na tabela ou ficar fora da tolerância.
    """
    por_mes = mensal.set_index("mes")

    linhas = []
    for mes_texto, oficial in IPCA_12M_IBGE.items():
        mes = pd.Period(mes_texto, freq="M")

        if mes not in por_mes.index:
            raise ValueError(
                f"Validação do IPCA: o mês de referência {mes} não existe na "
                f"tabela mensal, que vai de {por_mes.index[0]} a {por_mes.index[-1]}."
            )

        calculado = por_mes.at[mes, "ipca_12m"]
        if pd.isna(calculado):
            raise ValueError(
                f"Validação do IPCA: o mês {mes} existe na tabela mensal, mas sem "
                "IPCA em 12 meses (faltam meses anteriores; confira a data de "
                "início da extração)."
            )

        janela = por_mes.loc[mes - 11 : mes, "ipca_mes"]
        linhas.append(
            {
                "mes": mes,
                "calculado": calculado,
                "ibge": oficial,
                "diferenca": abs(calculado - oficial),
                "tolerancia": tolerancia_acumulado(janela),
            }
        )

    comparacao = pd.DataFrame(linhas).set_index("mes")
    fora = comparacao[comparacao["diferenca"] > comparacao["tolerancia"] + FOLGA_FLOAT]
    pior = comparacao["diferenca"].idxmax()

    print(
        f"Validação IPCA 12m x IBGE: {len(comparacao)} meses de referência "
        f"({comparacao.index[0]} a {comparacao.index[-1]}), "
        f"{len(comparacao) - len(fora)} dentro da tolerância; "
        f"maior diferença {comparacao.at[pior, 'diferenca']:.4f} p.p. em {pior} "
        f"(tolerância nesse mês: {comparacao.at[pior, 'tolerancia']:.4f} p.p.)"
    )

    if not fora.empty:
        raise ValueError(
            "IPCA em 12 meses fora da tolerância em relação ao IBGE:\n"
            + fora.round(4).to_string()
        )


if __name__ == "__main__":
    # Valida os arquivos já gravados, sem rodar o pipeline inteiro.
    diario_gravado = pd.read_csv(
        ARQUIVO_DIARIO, parse_dates=["data"], date_format="%Y-%m-%d"
    )
    mensal_gravado = pd.read_csv(ARQUIVO_MENSAL, dtype={"mes": str})
    mensal_gravado = mensal_gravado.assign(
        mes=pd.to_datetime(mensal_gravado["mes"], format="%Y-%m").dt.to_period("M")
    )

    validar_cdi_mensal(diario_gravado)
    validar_ipca_12m(mensal_gravado)
