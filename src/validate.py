"""Validação: confere os resultados do pipeline contra valores oficiais."""

import pandas as pd

from src.config import (
    ARQUIVO_MENSAL,
    DATA_INICIO_EXTRACAO,
    SERIE_VALIDACAO_CDI_MES,
)
from src.extract import baixar_serie_sgs, data_fim_padrao
from src.transform import CORRECOES_IBOV, ler_raw_ibov

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

# Fechamento oficial do Ibovespa no último pregão de cada ano.
# Fonte: B3 (estatísticas históricas do Ibovespa). Conferidos em 31/10/2026.
IBOV_FECHAMENTO_B3 = {
    "2021-12-30": 104822.44,
    "2022-12-29": 109734.60,
    "2023-12-28": 134185.24,
    "2024-12-30": 120283.40,
    "2025-12-30": 161125.37,
}

# O Yahoo traz o Ibovespa em pontos inteiros, e não dá para saber se ele
# arredonda ou corta os centavos. Nos dois casos, o erro fica abaixo de 1 ponto.
TOLERANCIA_IBOV_PONTOS = 1.0


# --- CDI -----------------------------------------------------------------------


def validar_cdi_mensal(mensal: pd.DataFrame) -> None:
    """Compara a coluna cdi_mes da tabela mensal com a série 4391 do SGS.

    A coluna já tem só meses fechados (calculados pelo índice D-1 no transform),
    então o número conferido é exatamente o que é gravado e exibido.

    Tolerância: 0,005 p.p. O cálculo usa a série diária com 6 casas, e só a
    4391 vem arredondada para 2 casas.

    Levanta ValueError se algum mês ficar fora da tolerância.
    """
    calculado = mensal.dropna(subset=["cdi_mes"]).set_index("mes")["cdi_mes"]

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
    # Só os meses com IPCA divulgado: a tabela pode ter um mês a mais, só com
    # o CDI, entre o fechamento do CDI e a divulgação do IPCA.
    por_mes = mensal.dropna(subset=["ipca_mes"]).set_index("mes")

    linhas = []
    for mes_texto, oficial in IPCA_12M_IBGE.items():
        mes = pd.Period(mes_texto, freq="M")

        if mes not in por_mes.index:
            raise ValueError(
                f"Validação do IPCA: o mês de referência {mes} não existe nos "
                f"dados do IPCA, que vão de {por_mes.index[0]} a {por_mes.index[-1]}."
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


# --- Ibovespa ------------------------------------------------------------------


def validar_ibovespa(ibov_yahoo: pd.DataFrame) -> None:
    """Compara o fechamento do Yahoo, ANTES das correções, com o oficial da B3.

    - Referências sem correção precisam bater dentro da tolerância; se algum
      dia ficar fora, levanta ValueError.
    - Cada correção é conferida contra o próprio Yahoo: se ainda diverge, é
      uma divergência conhecida; se passou a bater, a correção ficou
      obsoleta e o pipeline avisa (sem parar).

    Comparar o dado antes da correção evita a conta circular de validar um
    valor contra a mesma referência que o substituiu.
    """
    fechamento = ibov_yahoo.set_index("data")["fechamento"]

    linhas = []
    for data_texto, oficial in IBOV_FECHAMENTO_B3.items():
        if data_texto in CORRECOES_IBOV:
            continue  # tratada abaixo, junto com as correções

        data = pd.Timestamp(data_texto)
        if data not in fechamento.index:
            raise ValueError(
                f"Validação do Ibovespa: o fechamento de referência de "
                f"{data:%d/%m/%Y} não existe nos dados do Yahoo."
            )
        linhas.append(
            {
                "data": data,
                "yahoo": fechamento[data],
                "b3": oficial,
                "diferenca": abs(fechamento[data] - oficial),
            }
        )

    comparacao = pd.DataFrame(linhas).set_index("data")
    fora = comparacao[
        comparacao["diferenca"] > TOLERANCIA_IBOV_PONTOS + FOLGA_FLOAT
    ]
    pior = comparacao["diferenca"].idxmax()

    print(
        f"Validação Ibovespa x B3: {len(comparacao)} fechamentos de referência "
        f"sem correção, {len(comparacao) - len(fora)} dentro da tolerância; "
        f"maior diferença {comparacao.at[pior, 'diferenca']:.2f} pts em "
        f"{pior:%d/%m/%Y} (tolerância: {TOLERANCIA_IBOV_PONTOS:.0f} ponto)"
    )

    for data_texto, oficial in CORRECOES_IBOV.items():
        data = pd.Timestamp(data_texto)
        yahoo = fechamento[data]  # a existência já foi conferida no transform
        if abs(yahoo - oficial) > TOLERANCIA_IBOV_PONTOS + FOLGA_FLOAT:
            print(
                f"  Divergência conhecida, corrigida no processed: {data:%d/%m/%Y} "
                f"Yahoo {yahoo:.2f} x B3 {oficial:.2f}"
            )
        else:
            print(
                f"  AVISO: a correção de {data:%d/%m/%Y} parece obsoleta; o Yahoo "
                f"agora bate com a B3 ({yahoo:.2f} x {oficial:.2f}). "
                "Considere removê-la de CORRECOES_IBOV."
            )

    if not fora.empty:
        raise ValueError(
            "Ibovespa fora da tolerância em relação à B3:\n"
            + fora.round(2).to_string()
        )


if __name__ == "__main__":
    # Valida os dados já gravados, sem rodar o pipeline inteiro.
    mensal_gravado = pd.read_csv(ARQUIVO_MENSAL, dtype={"mes": str})
    mensal_gravado = mensal_gravado.assign(
        mes=pd.to_datetime(mensal_gravado["mes"], format="%Y-%m").dt.to_period("M")
    )

    validar_cdi_mensal(mensal_gravado)
    validar_ipca_12m(mensal_gravado)
    validar_ibovespa(ler_raw_ibov())
