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
COLUNAS_NIVEL = ["cdi_indice", "dolar", "ibov"]

# Correções de fechamentos do Ibovespa comprovadamente errados no Yahoo, pelo
# valor oficial. O raw mantém o valor do Yahoo; a correção vale só no processed.
# A validação confere, a cada execução, se cada correção ainda é necessária.
# Fonte: B3 (estatísticas históricas do Ibovespa). Conferido em 31/10/2026.
CORRECOES_IBOV = {
    # Yahoo: 110031 (queda de 0,19% no dia); oficial: queda de 0,46%.
    "2022-12-29": 109734.60,
}

# O Yahoo traz o Ibovespa em pontos inteiros: diferenças de até 1 ponto podem
# vir só do arredondamento ou corte dos centavos.
LIMITE_ARREDONDAMENTO_IBOV = 1.0

DIAS_SEMANA_PT = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]


# --- Leitura do raw ------------------------------------------------------------


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


def ler_raw_ibov() -> pd.DataFrame:
    """Lê data/raw/ibov.csv e devolve data, abertura e fechamento (do Yahoo).

    A data vem com o fuso da bolsa. O fuso é removido SEM conversão (a hora
    local é mantida) e toda hora precisa ser 00:00. Se não for, o carimbo não
    é o esperado e o pipeline para, em vez de arriscar mudar o dia.
    """
    bruto = pd.read_csv(DIR_RAW / "ibov.csv")

    colunas_esperadas = {"Date", "Open", "Close"}
    if not colunas_esperadas.issubset(bruto.columns):
        raise ValueError(
            f"ibov: colunas inesperadas no bruto {list(bruto.columns)}; "
            f"esperava pelo menos {sorted(colunas_esperadas)}."
        )

    datas = pd.to_datetime(bruto["Date"])
    if datas.dt.tz is not None:
        datas = datas.dt.tz_localize(None)  # tira o fuso mantendo a hora local

    fora_da_meia_noite = datas != datas.dt.normalize()
    if fora_da_meia_noite.any():
        raise ValueError(
            "ibov: há datas fora da meia-noite local "
            f"(ex.: {datas[fora_da_meia_noite].iloc[0]}); o dia pode estar deslocado."
        )

    df = pd.DataFrame(
        {
            "data": datas.dt.as_unit("ns"),
            "abertura": pd.to_numeric(bruto["Open"]),
            "fechamento": pd.to_numeric(bruto["Close"]),
        }
    )

    if df["data"].duplicated().any():
        raise ValueError("ibov: há datas duplicadas no arquivo bruto.")
    if not df["data"].is_monotonic_increasing:
        raise ValueError("ibov: as datas do arquivo bruto estão fora de ordem.")

    fim_de_semana = df["data"].dt.dayofweek >= 5
    if fim_de_semana.any():
        exemplos = ", ".join(f"{d:%d/%m/%Y}" for d in df.loc[fim_de_semana, "data"].head(5))
        raise ValueError(f"ibov: há datas em fim de semana: {exemplos}.")

    if df["fechamento"].isna().any() or (df["fechamento"] <= 0).any():
        raise ValueError("ibov: há fechamentos vazios ou não positivos no arquivo bruto.")

    return df


# --- Ibovespa: correções e conferência informativa -----------------------------


def aplicar_correcoes_ibov(ibov: pd.DataFrame) -> pd.DataFrame:
    """Devolve as colunas data e ibov (fechamento) com as correções aplicadas.

    Cada correção aplicada é impressa. Uma correção para uma data sem pregão
    nos dados do Yahoo para o pipeline: a tabela de correções estaria errada.
    """
    fechamento = ibov.set_index("data")["fechamento"]

    correcoes = pd.Series(CORRECOES_IBOV, dtype="float64")
    correcoes.index = pd.to_datetime(correcoes.index, format="%Y-%m-%d").as_unit("ns")

    sem_pregao = correcoes.index.difference(fechamento.index)
    if not sem_pregao.empty:
        datas = ", ".join(f"{d:%d/%m/%Y}" for d in sem_pregao)
        raise ValueError(f"ibov: correção para data sem pregão no Yahoo: {datas}.")

    for data, valor in correcoes.items():
        print(
            f"Correção ibov em {data:%d/%m/%Y}: "
            f"{fechamento[data]:.2f} (Yahoo) -> {valor:.2f} (B3)"
        )

    corrigido = correcoes.combine_first(fechamento).rename_axis("data").rename("ibov")
    return corrigido.reset_index()


def relatar_fechamento_x_abertura(ibov: pd.DataFrame) -> None:
    """Informativo: compara o fechamento de cada pregão com a abertura do
    pregão seguinte, no próprio Yahoo e antes das correções.

    Se a abertura do Yahoo costuma repetir o fechamento anterior, os dias
    que fogem disso são candidatos a fechamento errado, para conferir na B3.
    Diferenças de até 1 ponto são explicadas pelos pontos inteiros do Yahoo
    (o mesmo raciocínio da tolerância da validação). Não para o pipeline.
    """
    diferenca = (ibov["abertura"].shift(-1) - ibov["fechamento"]).abs().dropna()

    iguais = int((diferenca == 0).sum())
    ate_1 = int((diferenca <= LIMITE_ARREDONDAMENTO_IBOV).sum())
    print(
        f"Fechamento x abertura seguinte (ibov): {len(diferenca)} pares de pregões; "
        f"{iguais} iguais e {ate_1} com diferença de até 1 ponto."
    )

    acima = diferenca[diferenca > LIMITE_ARREDONDAMENTO_IBOV]
    if acima.empty:
        print("  Nenhuma diferença acima de 1 ponto.")
        return

    maiores = acima.nlargest(10)
    detalhes = ", ".join(
        f"{ibov.at[i, 'data']:%d/%m/%Y} ({valor:.0f} pts)" for i, valor in maiores.items()
    )
    print(
        f"  {len(acima)} acima de 1 ponto; as maiores, pela data do fechamento: {detalhes}"
    )


# --- Calendários ---------------------------------------------------------------


def relatar_calendarios(datas_por_serie: dict[str, pd.Series]) -> None:
    """Informa, para cada série, até quando ela vai e TODAS as datas das
    outras séries que faltam DENTRO do seu próprio período.

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
            lista = ", ".join(
                f"{d:%d/%m/%Y} ({DIAS_SEMANA_PT[d.dayofweek]})" for d in faltando
            )
            mensagem += f"{len(faltando)} datas das outras séries faltando: {lista}"
        print(mensagem)


# --- Tabelas processadas -------------------------------------------------------


def montar_diario() -> pd.DataFrame:
    """Tabela diária com CDI, dólar e Ibovespa, alinhados pela data."""
    cdi = ler_raw_sgs("cdi")
    ptax = ler_raw_sgs("ptax")
    ibov = ler_raw_ibov()

    # Cálculos do CDI no calendário da própria série, ANTES de alinhar (D-1).
    cdi_calculado = pd.DataFrame(
        {
            "data": cdi["data"],
            "cdi_taxa_ano": anualizar_taxa_diaria(cdi["valor"]),
            "cdi_indice": indice_acumulado_d1(cdi["valor"]),
        }
    )
    dolar = pd.DataFrame({"data": ptax["data"], "dolar": ptax["valor"]})
    ibov_corrigido = aplicar_correcoes_ibov(ibov)

    relatar_fechamento_x_abertura(ibov)
    relatar_calendarios({"cdi": cdi["data"], "ptax": ptax["data"], "ibov": ibov["data"]})

    # União das datas: nenhuma data de nenhuma série é descartada.
    diario = (
        cdi_calculado.merge(dolar, on="data", how="outer")
        .merge(ibov_corrigido, on="data", how="outer")
        .sort_values("data", ignore_index=True)
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
