"""Dashboard de indicadores de mercado (Streamlit).

Só lê data/processed; não chama nenhuma API.
Antes de abrir, rode o pipeline: python -m src.pipeline
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from src.config import ARQUIVO_DIARIO, DATA_INICIO_ANALISE
from src.indicadores import base_100


def formatar_pct(valor: float) -> str:
    """13.6512 -> '13,65%' (vírgula decimal, padrão brasileiro)."""
    return f"{valor:.2f}%".replace(".", ",")


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

ultima = diario.iloc[-1]

# --- Cartão: CDI ao ano --------------------------------------------------------

st.metric("CDI ao ano", formatar_pct(ultima["cdi_taxa_ano"]))
st.caption(f"Taxa de {ultima['data']:%d/%m/%Y}, anualizada em 252 dias úteis.")

# --- Linha: CDI em base 100 ----------------------------------------------------

data_min = diario["data"].iloc[0].date()
data_max = diario["data"].iloc[-1].date()

inicio = st.date_input(
    "Início da comparação",
    value=data_min,
    min_value=data_min,
    max_value=data_max,
    format="DD/MM/YYYY",
)

# Primeiro dia com dado a partir da data escolhida (se for fim de semana ou
# feriado, a aplicação começa no próximo dia útil).
periodo = diario[diario["data"] >= pd.Timestamp(inicio)]

# Uma linha precisa de pelo menos dois pontos. Em vez de esconder datas no
# seletor, avisa e não desenha; o resto do dashboard continua sendo exibido.
if len(periodo) < 2:
    st.warning(
        f"O período a partir de {periodo['data'].iloc[0]:%d/%m/%Y} tem só "
        f"{len(periodo)} dia com dado. Escolha uma data inicial anterior "
        "para ver a evolução."
    )
else:
    grafico = pd.DataFrame(
        {
            "data": periodo["data"],
            "CDI": base_100(periodo["cdi_indice"]),
        }
    )

    fig = px.line(
        grafico,
        x="data",
        y="CDI",
        title=f"R$ 100 aplicados no CDI em {periodo['data'].iloc[0]:%d/%m/%Y}",
    )
    fig.update_traces(hovertemplate="%{x|%d/%m/%Y}<br>R$ %{y:.2f}<extra></extra>")
    fig.update_layout(
        separators=",.",            # vírgula decimal e ponto de milhar
        xaxis_title=None,
        yaxis_title="R$",
        xaxis_tickformat="%m/%Y",   # meses em número, sem nomes em inglês
    )

    st.plotly_chart(fig)
