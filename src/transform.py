"""Transformação: lê data/raw, padroniza tipos e monta as tabelas processadas."""

import pandas as pd

from src.config import DIR_RAW
from src.indicadores import (
    anualizar_taxa_diaria,
    indice_acumulado,
    indice_acumulado_d1,
    variacao_acumulada,
)

# Colunas de nível (índice ou preço): numa data sem dado da própria série,
# repetem o último valor, mas só ENTRE datas reais, nunca depois do fim.
COLUNAS_NIVEL = ["cdi_indice", "dolar"]


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


def relatar_calendarios(datas_por_serie: dict[str, pd.Series]) -> None:
    """Informa, para cada série, até quando ela vai e quais datas das outras
    séries faltam DENTRO do seu próprio período.

    O fim de cada série não conta como falta: séries publicadas em horários
    diferentes terminam em dias diferentes, e isso é esperado.
    """
    uniao = pd.DatetimeIndex(
        pd.concat(list(datas_por_serie.values())).unique()
    ).sort_values()

    for nome, datas in datas_por_serie.items():
        inicio, fim = datas.min(), datas.max()
        dentro = uniao[(uniao >= inicio) & (uniao <= fim)]
        faltando = dentro.difference(pd.DatetimeIndex(datas))

        mensagem = (
            f"Calendário {nome}: {len(datas)} datas, "
            f"de {inicio:%d/%m/%Y} a {fim:%d/%m/%Y}; "
        )
        if faltando.empty:
            mensagem += "nenhuma data das outras séries faltando nesse período."
        else:
            exemplos = ", ".join(f"{d:%d/%m/%Y}" for d in faltando[:10])
            reticencias = " ..." if len(faltando) > 10 else ""
            mensagem += (
                f"{len(faltando)} datas das outras séries faltando: "
                f"{exemplos}{reticencias}"
            )
        print(mensagem)


def montar_diario() -> pd.DataFrame:
    """Tabela diária com CDI e dólar, alinhados pela data."""
    cdi = ler_raw_sgs("cdi")
    ptax = ler_raw_sgs("ptax")

    # Cálculos do CDI no calendário da própria série, ANTES de alinhar (D-1).
    cdi_calculado = pd.DataFrame(
        {
            "data": cdi["data"],
            "cdi_taxa_ano": anualizar_taxa_diaria(cdi["valor"]),
            "cdi_indice": indice_acumulado_d1(cdi["valor"]),
        }
    )
    dolar = pd.DataFrame({"data": ptax["data"], "dolar": ptax["valor"]})

    relatar_calendarios({"cdi": cdi["data"], "ptax": ptax["data"]})

    # União das datas: nenhuma data de nenhuma série é descartada.
    diario = cdi_calculado.merge(dolar, on="data", how="outer").sort_values(
        "data", ignore_index=True
    )

    # Atribuição direta no próprio DataFrame (não é encadeada; ok com Copy-on-Write).
    # A taxa ao ano NÃO é preenchida: ela só existe nas datas reais do CDI.
    diario[COLUNAS_NIVEL] = diario[COLUNAS_NIVEL].ffill(limit_area="inside")

    return diario


def ler_raw_sgs_mensal(nome: str) -> pd.DataFrame:
    """Lê uma série mensal do raw e devolve as colunas mes (período) e valor.

    O SGS data cada mês no dia 1, mas o valor representa o mês inteiro; por
    isso a data vira um período mensal (ex.: 2026-09), e não um dia.
    """
    df = ler_raw_sgs(nome)  # já confere duplicatas, ordem e vazios

    if (df["data"].dt.day != 1).any():
        raise ValueError(f"{nome}: esperava todas as datas no dia 1 (rótulo do mês).")

    meses = df["data"].dt.to_period("M")

    # Sem duplicatas e em ordem, o tamanho igual ao do intervalo completo
    # garante que nenhum mês está faltando.
    esperado = pd.period_range(meses.iloc[0], meses.iloc[-1], freq="M")
    if len(meses) != len(esperado):
        raise ValueError(
            f"{nome}: há meses faltando entre {meses.iloc[0]} e {meses.iloc[-1]}."
        )

    return pd.DataFrame({"mes": meses, "valor": df["valor"]})


def montar_mensal() -> pd.DataFrame:
    """Tabela mensal. Por enquanto só com o IPCA; o CDI mensal entra na Etapa 5."""
    ipca = ler_raw_sgs_mensal("ipca")
    indice = indice_acumulado(ipca["valor"])

    return pd.DataFrame(
        {
            "mes": ipca["mes"],
            "ipca_mes": ipca["valor"],
            "ipca_indice": indice,
            # Os 12 primeiros meses ficam vazios: não há 12 meses anteriores.
            "ipca_12m": variacao_acumulada(indice, 12),
        }
    )
