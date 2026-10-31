"""Dashboard de indicadores de mercado (Streamlit).

Só lê data/processed; não chama nenhuma API.
Antes de abrir, rode o pipeline: python -m src.pipeline
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.config import ARQUIVO_DIARIO, ARQUIVO_MENSAL, DATA_INICIO_ANALISE
from src.indicadores import base_100

# Espaçamento entre rótulos do eixo, em milissegundos (unidade do Plotly).
QUINZE_DIAS_MS = 15 * 24 * 60 * 60 * 1000

# Séries diárias do gráfico comparativo: coluna do diario.csv -> nome na legenda.
SERIES_DIARIAS = {"cdi_indice": "CDI", "dolar": "Dólar"}

# Cor fixa de cada série em todos os gráficos (paleta Okabe-Ito, que continua
# distinguível para quem tem daltonismo). Definida por série, para que as cores
# não mudem quando outra série entrar.
CORES = {
    "CDI": "#0072B2",       # azul
    "Dólar": "#009E73",     # verde
    "IPCA": "#CC79A7",      # roxo-avermelhado
    "Ibovespa": "#D55E00",  # vermelho-alaranjado
}

# Abreviações fixas: strftime("%b") depende do idioma do sistema operacional.
MESES_PT = ["jan", "fev", "mar", "abr", "mai", "jun",
            "jul", "ago", "set", "out", "nov", "dez"]


def formatar_numero(valor: float, casas: int) -> str:
    """1234.5 -> '1.234,50' (ponto de milhar e vírgula decimal)."""
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_pct(valor: float) -> str:
    """13.6512 -> '13,65%'."""
    return f"{formatar_numero(valor, 2)}%"


def rotulo_mes(mes: pd.Period) -> str:
    """Period('2026-09') -> 'set/2026'."""
    return f"{MESES_PT[mes.month - 1]}/{mes.year}"


def ultimo_valido(tabela: pd.DataFrame, coluna: str) -> pd.Series:
    """Última linha em que `coluna` tem dado.

    Como o preenchimento só acontece entre datas reais, o último valor
    preenchido de qualquer coluna é sempre um dado real da fonte.
    """
    return tabela.dropna(subset=[coluna]).iloc[-1]


def pontos_ipca(mensal: pd.DataFrame, inicio: pd.Timestamp) -> pd.DataFrame:
    """Pontos do IPCA em base 100 a partir de `inicio`.

    Base: índice do mês ANTERIOR ao mês de início, para que a inflação do
    mês de início conte inteira (regra conservadora: num início no meio do
    mês, superestima a inflação em vez de subestimar).
    O ponto 100 fica na própria data de início, junto com as outras linhas;
    os demais ficam no último dia de cada mês divulgado.

    Devolve tabela vazia se o índice do mês-base não estiver disponível.
    """
    indice = mensal.set_index("mes")["ipca_indice"]
    mes_inicio = inicio.to_period("M")
    mes_base = mes_inicio - 1

    if mes_base not in indice.index:
        return pd.DataFrame(columns=["data", "valor", "rotulo"])

    base = indice[mes_base]
    meses = indice.loc[mes_inicio:]  # meses divulgados a partir do início

    return pd.DataFrame(
        {
            "data": [inicio, *(m.end_time.normalize() for m in meses.index)],
            "valor": [100.0, *(meses / base * 100)],
            "rotulo": [f"base {rotulo_mes(mes_base)}",
                       *(rotulo_mes(m) for m in meses.index)],
        }
    )


st.set_page_config(page_title="Indicadores de mercado", layout="wide")
st.title("Indicadores de mercado")

# --- Dados ---------------------------------------------------------------------

faltando = [c.name for c in (ARQUIVO_DIARIO, ARQUIVO_MENSAL) if not c.exists()]
if faltando:
    st.error(
        f"Arquivo(s) não encontrado(s) em data/processed: {', '.join(faltando)}. "
        "Rode antes: python -m src.pipeline"
    )
    st.stop()

diario = pd.read_csv(ARQUIVO_DIARIO, parse_dates=["data"], date_format="%Y-%m-%d")

# Só o período de análise: a folga de 12 meses existe para os cálculos,
# não para ser exibida.
diario = diario[diario["data"] >= pd.Timestamp(DATA_INICIO_ANALISE)]

# O mês vem como texto (2026-09) e volta a ser período. O mensal NÃO é
# cortado no início da análise: a base do IPCA para 01/10/2021 é set/2021.
mensal = pd.read_csv(ARQUIVO_MENSAL, dtype={"mes": str})
mensal = mensal.assign(
    mes=pd.to_datetime(mensal["mes"], format="%Y-%m").dt.to_period("M")
)

# --- Cartões: situação atual, cada um com a data do próprio dado ----------------

col_cdi, col_dolar, col_ipca = st.columns(3)

with col_cdi:
    # A taxa ao ano nunca é preenchida: ela marca as datas reais do CDI.
    cdi = ultimo_valido(diario, "cdi_taxa_ano")
    st.metric("CDI ao ano", formatar_pct(cdi["cdi_taxa_ano"]))
    st.caption(f"Taxa de {cdi['data']:%d/%m/%Y}, anualizada em 252 dias úteis.")

with col_dolar:
    dolar = ultimo_valido(diario, "dolar")
    st.metric("Dólar (PTAX venda)", f"R$ {formatar_numero(dolar['dolar'], 4)}")
    st.caption(f"Cotação de {dolar['data']:%d/%m/%Y}.")

with col_ipca:
    ipca = ultimo_valido(mensal, "ipca_12m")
    st.metric(f"IPCA 12 meses até {rotulo_mes(ipca['mes'])}", formatar_pct(ipca["ipca_12m"]))
    st.caption("Inflação oficial (IBGE), divulgada no mês seguinte ao de referência.")

# --- Gráfico comparativo em base 100 -------------------------------------------

# Séries diárias: só datas em que TODAS têm dado, para compararem o mesmo
# período. O IPCA entra com os próprios pontos mensais, da tabela mensal.
completo = diario[["data", *SERIES_DIARIAS]].dropna()

data_min = completo["data"].iloc[0].date()
data_max = completo["data"].iloc[-1].date()

inicio = st.date_input(
    "Início da comparação",
    value=data_min,
    min_value=data_min,
    max_value=data_max,
    format="DD/MM/YYYY",
)

# Primeiro dia com dado a partir da data escolhida (se for fim de semana ou
# feriado, a aplicação começa no próximo dia útil).
periodo = completo[completo["data"] >= pd.Timestamp(inicio)]

# Uma linha precisa de pelo menos dois pontos. Em vez de esconder datas no
# seletor, avisa e não desenha; o resto do dashboard continua sendo exibido.
if len(periodo) < 2:
    st.warning(
        f"O período a partir de {periodo['data'].iloc[0]:%d/%m/%Y} tem só "
        f"{len(periodo)} dia com dado. Escolha uma data inicial anterior "
        "para ver a evolução."
    )
else:
    inicio_real = periodo["data"].iloc[0]
    fig = go.Figure()

    for coluna, nome in SERIES_DIARIAS.items():
        fig.add_trace(
            go.Scatter(
                x=periodo["data"],
                y=base_100(periodo[coluna]),
                name=nome,
                mode="lines",
                line=dict(color=CORES[nome]),
                hovertemplate=f"{nome}: R$ %{{y:.2f}}<extra></extra>",
            )
        )

    # IPCA: precisa de pelo menos um mês divulgado depois do ponto-base.
    pontos = pontos_ipca(mensal, inicio_real)
    mes_base = rotulo_mes(inicio_real.to_period("M") - 1)
    if len(pontos) >= 2:
        fig.add_trace(
            go.Scatter(
                x=pontos["data"],
                y=pontos["valor"],
                name="IPCA",
                mode="lines+markers",
                line=dict(color=CORES["IPCA"]),
                customdata=pontos["rotulo"],
                # O mês no texto evita confundir o ponto mensal com o valor
                # do dia sob o cursor (a caixa unificada mostra o mais próximo).
                hovertemplate="IPCA (%{customdata}): R$ %{y:.2f}<extra></extra>",
            )
        )
        nota_ipca = (
            "IPCA: quanto os R$ 100 precisariam valer para manter o poder de "
            f"compra, com a inflação desde o início do mês da data escolhida "
            f"(base: índice de {mes_base}); pontos nos fins de mês divulgados, "
            f"até {pontos['rotulo'].iloc[-1]}."
        )
    else:
        nota_ipca = (
            "IPCA: ainda não há mês divulgado a partir de "
            f"{rotulo_mes(inicio_real.to_period('M'))}, por isso não aparece."
        )

    fig.update_layout(
        title=f"R$ 100 aplicados em {inicio_real:%d/%m/%Y}",
        separators=",.",            # vírgula decimal e ponto de milhar
        xaxis_title=None,
        yaxis_title="R$",
        hovermode="x unified",      # uma caixa com todas as séries na mesma data
        xaxis_hoverformat="%d/%m/%Y",
        # O formato dos rótulos depende do espaçamento que o Plotly escolhe
        # (vale também com zoom). Os passos automáticos do Plotly saltam de
        # 14 dias direto para 1 mês, então o corte em 15 dias separa
        # "menos de um mês entre rótulos" de "um mês ou mais" sem depender
        # de como o Plotly desempata um valor exatamente na fronteira.
        xaxis_tickformatstops=[
            dict(dtickrange=[None, QUINZE_DIAS_MS], value="%d/%m/%y"),
            dict(dtickrange=[QUINZE_DIAS_MS, None], value="%m/%Y"),
        ],
    )

    st.plotly_chart(fig)
    st.caption(
        "CDI: 100% do CDI, bruto de impostos. "
        "Dólar: variação da PTAX venda, como dólar parado, sem rendimento. "
        f"{nota_ipca} "
        f"CDI e dólar vão até {periodo['data'].iloc[-1]:%d/%m/%Y}, "
        "a última data em que os dois têm dado."
    )
