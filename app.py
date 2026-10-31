"""Dashboard de indicadores de mercado (Streamlit).

Só lê data/processed; não chama nenhuma API.
Antes de abrir, rode o pipeline: python -m src.pipeline
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from src.config import ARQUIVO_DIARIO, DATA_INICIO_ANALISE
from src.indicadores import base_100

# Espaçamento entre rótulos do eixo, em milissegundos (unidade do Plotly).
QUINZE_DIAS_MS = 15 * 24 * 60 * 60 * 1000

# Séries do gráfico comparativo: coluna do diario.csv -> nome na legenda.
SERIES_GRAFICO = {"cdi_indice": "CDI", "dolar": "Dólar"}


def formatar_numero(valor: float, casas: int) -> str:
    """1234.5 -> '1.234,50' (ponto de milhar e vírgula decimal)."""
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_pct(valor: float) -> str:
    """13.6512 -> '13,65%'."""
    return f"{formatar_numero(valor, 2)}%"


def ultimo_valido(tabela: pd.DataFrame, coluna: str) -> pd.Series:
    """Última linha em que `coluna` tem dado.

    Como o preenchimento só acontece entre datas reais, o último valor
    preenchido de qualquer coluna é sempre um dado real da fonte.
    """
    return tabela.dropna(subset=[coluna]).iloc[-1]


st.set_page_config(page_title="Indicadores de mercado", layout="wide")
st.title("Indicadores de mercado")

# --- Dados ---------------------------------------------------------------------

if not ARQUIVO_DIARIO.exists():
    st.error(
        "Arquivo data/processed/diario.csv não encontrado. "
        "Rode antes: python -m src.pipeline"
    )
    st.stop()

diario = pd.read_csv(ARQUIVO_DIARIO, parse_dates=["data"], date_format="%Y-%m-%d")

# Só o período de análise: a folga de 12 meses existe para os cálculos,
# não para ser exibida.
diario = diario[diario["data"] >= pd.Timestamp(DATA_INICIO_ANALISE)]

# --- Cartões: situação atual, cada um com a data do próprio dado ----------------

col_cdi, col_dolar = st.columns(2)

with col_cdi:
    # A taxa ao ano nunca é preenchida: ela marca as datas reais do CDI.
    cdi = ultimo_valido(diario, "cdi_taxa_ano")
    st.metric("CDI ao ano", formatar_pct(cdi["cdi_taxa_ano"]))
    st.caption(f"Taxa de {cdi['data']:%d/%m/%Y}, anualizada em 252 dias úteis.")

with col_dolar:
    dolar = ultimo_valido(diario, "dolar")
    st.metric("Dólar (PTAX venda)", f"R$ {formatar_numero(dolar['dolar'], 4)}")
    st.caption(f"Cotação de {dolar['data']:%d/%m/%Y}.")

# --- Gráfico comparativo em base 100 -------------------------------------------

# Só datas em que TODAS as séries do gráfico têm dado, para que as linhas
# comparem exatamente o mesmo período.
completo = diario[["data", *SERIES_GRAFICO]].dropna()

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
    grafico = periodo[["data"]].assign(
        **{rotulo: base_100(periodo[coluna]) for coluna, rotulo in SERIES_GRAFICO.items()}
    )

    fig = px.line(
        grafico,
        x="data",
        y=list(SERIES_GRAFICO.values()),
        title=f"R$ 100 aplicados em {periodo['data'].iloc[0]:%d/%m/%Y}",
    )
    fig.update_traces(hovertemplate="%{fullData.name}: R$ %{y:.2f}<extra></extra>")
    fig.update_layout(
        separators=",.",            # vírgula decimal e ponto de milhar
        xaxis_title=None,
        yaxis_title="R$",
        legend_title_text=None,
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
        f"O gráfico vai até {periodo['data'].iloc[-1]:%d/%m/%Y}, "
        "a última data em que todas as séries têm dado."
    )
