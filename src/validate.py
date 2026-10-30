"""Validação: confere os resultados do pipeline contra valores oficiais."""

import pandas as pd

from src.config import ARQUIVO_DIARIO, DATA_INICIO_EXTRACAO, SERIE_VALIDACAO_CDI_MES
from src.extract import baixar_serie_sgs, data_fim_padrao
from src.indicadores import variacao_mensal_d1

# A 4391 vem com 2 casas decimais: um valor arredondado assim pode estar a até
# 0,005 do valor exato. O 1e-9 só absorve a imprecisão de ponto flutuante.
TOLERANCIA_PP = 0.005 + 1e-9


def validar_cdi_mensal(diario: pd.DataFrame) -> None:
    """Compara o CDI mensal do índice D-1 com a série 4391 do SGS (meses fechados).

    Levanta ValueError se algum mês ficar fora da tolerância.
    """
    calculado = variacao_mensal_d1(diario["data"], diario["cdi_indice"])

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
    fora = comparacao[comparacao["diferenca"] > TOLERANCIA_PP]

    print(
        f"Validação CDI x SGS {SERIE_VALIDACAO_CDI_MES}: "
        f"{len(comparacao)} meses fechados "
        f"({comparacao.index[0]} a {comparacao.index[-1]}), "
        f"{len(comparacao) - len(fora)} dentro da tolerância; "
        f"maior diferença {comparacao['diferenca'].max():.4f} p.p."
    )

    if not fora.empty:
        raise ValueError(
            "CDI mensal fora da tolerância em relação à 4391:\n"
            + fora.round(4).to_string()
        )


if __name__ == "__main__":
    # Valida o arquivo já gravado, sem rodar o pipeline inteiro.
    diario_gravado = pd.read_csv(
        ARQUIVO_DIARIO, parse_dates=["data"], date_format="%Y-%m-%d"
    )
    validar_cdi_mensal(diario_gravado)
