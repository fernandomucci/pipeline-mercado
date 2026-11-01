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
SERIES_DIARIAS = {"cdi_indice": "CDI", "ibov": "Ibovespa", "dolar": "Dólar"}

# Ordem das séries nos cartões e na legenda: taxas em % juntas (juro x
# inflação), depois os preços de mercado.
ORDEM_SERIES = ["CDI", "IPCA", "Ibovespa", "Dólar"]

# Cor fixa de cada série em todos os gráficos (paleta Okabe-Ito, que continua
# distinguível para quem tem daltonismo). Definida por série, para que as cores
# não mudem quando outra série entrar.
CORES = {
    "CDI": "#0072B2",       # azul
    "Dólar": "#009E73",     # verde
    "IPCA": "#CC79A7",      # roxo-avermelhado
    "Ibovespa": "#D55E00",  # vermelho-alaranjado
}

# Juro real: série derivada, que não é nenhuma das quatro, em cinza médio, que
# funciona no tema claro e no escuro do Streamlit. A faixa abaixo do zero é
# semitransparente pelo mesmo motivo.
COR_JURO_REAL = "#8C8C8C"
COR_FAIXA_NEGATIVA = "rgba(140, 140, 140, 0.15)"

# Meta de inflação (IPCA acumulado em 12 meses), no regime de meta contínua em
# vigor desde 2025: centro de 3% e intervalo de tolerância de 1,5% a 4,5%.
# Fonte: Conselho Monetário Nacional (CMN), Resolução CMN nº 5.141/2024.
# Valor fixo: mudanças precisam ser anunciadas com 36 meses de antecedência.
META_IPCA = 3.0
PISO_META_IPCA = 1.5
TETO_META_IPCA = 4.5

# Altura dos dois gráficos, em pixels: iguais e lado a lado. Ajuste olhando a tela.
ALTURA_GRAFICOS = 350

# Margens pequenas: as padrão do Plotly (~100 px em cima, ~80 nos lados e
# embaixo) comeriam boa parte de um gráfico desta altura. Os rótulos dos
# eixos ampliam a margem sozinhos quando precisam (automargin).
MARGENS_GRAFICOS = dict(l=10, r=10, t=10, b=10)

# Rótulo das notas recolhidas: carrega a principal ressalva, visível sem abrir.
ROTULO_NOTAS = "Notas (valores brutos de impostos)"

# Abreviações fixas: strftime("%b") depende do idioma do sistema operacional.
MESES_PT = ["jan", "fev", "mar", "abr", "mai", "jun",
            "jul", "ago", "set", "out", "nov", "dez"]


# --- Formatação ----------------------------------------------------------------


def formatar_numero(valor: float, casas: int) -> str:
    """1234.5 -> '1.234,50' (ponto de milhar e vírgula decimal)."""
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_pct(valor: float) -> str:
    """13.6512 -> '13,65%'."""
    return f"{formatar_numero(valor, 2)}%"


def formatar_pct_curto(valor: float) -> str:
    """3.0 -> '3%' e 4.5 -> '4,5%' (sem zeros à direita)."""
    return f"{valor:g}%".replace(".", ",")


def rotulo_mes(mes: pd.Period) -> str:
    """Period('2026-09') -> 'set/2026'."""
    return f"{MESES_PT[mes.month - 1]}/{mes.year}"


# --- Dados para os gráficos ----------------------------------------------------


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

    Usa só os meses com IPCA divulgado: a tabela mensal pode ter um mês a
    mais, só com o CDI. Devolve tabela vazia se o índice do mês-base não
    estiver disponível.
    """
    indice = mensal.dropna(subset=["ipca_indice"]).set_index("mes")["ipca_indice"]
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


def faixa_eixo_y(valores: pd.Series) -> tuple[float, float]:
    """Intervalo do eixo y que contém os valores E o zero, com uma folga.

    Sem forçar o zero, um período todo positivo deixaria a linha de empate e
    a faixa abaixo dela fora do gráfico.
    """
    menor = min(float(valores.min()), 0.0)
    maior = max(float(valores.max()), 0.0)
    folga = 0.08 * (maior - menor) or 1.0
    return menor - folga, maior + folga


def layout_grafico(inicio: pd.Timestamp, fim: pd.Timestamp) -> dict:
    """Configurações comuns aos dois gráficos: tamanho, margens e eixo de datas."""
    return dict(
        height=ALTURA_GRAFICOS,
        margin=MARGENS_GRAFICOS,
        xaxis_automargin=True,
        yaxis_automargin=True,
        separators=",.",            # vírgula decimal e ponto de milhar
        xaxis_title=None,
        # Intervalo definido à mão: com marcadores numa série, o Plotly deixa
        # 5% de margem em cada ponta do eixo (uns 3 meses em 5 anos).
        xaxis_range=[inicio, fim],
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


# --- Página --------------------------------------------------------------------

st.set_page_config(page_title="Indicadores de mercado", layout="wide")

# Título menor que o st.title: a página é um painel e a altura é o recurso escasso.
st.subheader("Indicadores de mercado")
st.caption(
    "Fontes: Banco Central (SGS) para CDI, PTAX e IPCA; Yahoo Finance, via "
    f"yfinance, para o Ibovespa. Dados desde {DATA_INICIO_ANALISE:%d/%m/%Y}; "
    "a data de cada número está no próprio cartão."
)

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

# --- Cartões: cada um com a data do próprio dado; detalhes no "?" ----------------

col_cdi, col_ipca, col_ibov, col_dolar = st.columns(4)

with col_cdi:
    # A taxa ao ano nunca é preenchida: ela marca as datas reais do CDI.
    cdi = ultimo_valido(diario, "cdi_taxa_ano")
    st.metric(
        "CDI ao ano",
        formatar_pct(cdi["cdi_taxa_ano"]),
        help="Taxa DI do dia, anualizada em 252 dias úteis.",
    )
    st.caption(f"Taxa de {cdi['data']:%d/%m/%Y}.")

with col_ipca:
    ipca = ultimo_valido(mensal, "ipca_12m")
    st.metric(
        f"IPCA 12 meses até {rotulo_mes(ipca['mes'])}",
        formatar_pct(ipca["ipca_12m"]),
        help="Inflação oficial (IBGE), acumulada em 12 meses e divulgada no mês "
        "seguinte ao de referência.",
    )
    # A meta fica visível: sem ela, o número fica solto.
    st.caption(
        f"Meta: {formatar_pct_curto(META_IPCA)}, intervalo de "
        f"{formatar_pct_curto(PISO_META_IPCA)} a {formatar_pct_curto(TETO_META_IPCA)}."
    )

with col_ibov:
    ibov = ultimo_valido(diario, "ibov")
    # Sem decimais: o Yahoo traz o Ibovespa em pontos inteiros.
    st.metric(
        "Ibovespa (pontos)",
        formatar_numero(ibov["ibov"], 0),
        help="Fechamento em pontos inteiros, como vem do Yahoo Finance (via yfinance).",
    )
    st.caption(f"Fechamento de {ibov['data']:%d/%m/%Y}.")

with col_dolar:
    dolar = ultimo_valido(diario, "dolar")
    st.metric(
        "Dólar (PTAX venda)",
        f"R$ {formatar_numero(dolar['dolar'], 4)}",
        help="Taxa de referência calculada pelo Banco Central e usada por empresas "
        "e contratos, não a cotação para comprar dólar.",
    )
    st.caption(f"Cotação de {dolar['data']:%d/%m/%Y}.")

# --- Dois gráficos lado a lado ---------------------------------------------------

col_esq, col_dir = st.columns([3, 2], gap="large")

# --- Esquerda: quanto R$ 100 viraram (comparativo em base 100) -------------------

with col_esq:
    # Séries diárias: só datas em que TODAS têm dado, para compararem o mesmo
    # período. O IPCA entra com os próprios pontos mensais, da tabela mensal.
    completo = diario[["data", *SERIES_DIARIAS]].dropna()

    data_min = completo["data"].iloc[0].date()
    data_max = completo["data"].iloc[-1].date()

    # Título e data na mesma linha, formando uma frase. O seletor fica dentro
    # desta coluna porque só vale para este gráfico.
    col_titulo, col_data = st.columns([5, 2], vertical_alignment="center")
    with col_titulo:
        st.markdown("#### Quanto R$ 100 viraram desde")
    with col_data:
        inicio = st.date_input(
            "Início da comparação",  # oculto na tela; a frase faz o papel do rótulo
            value=data_min,
            min_value=data_min,
            max_value=data_max,
            format="DD/MM/YYYY",
            label_visibility="collapsed",
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
        fim_real = periodo["data"].iloc[-1]
        fig = go.Figure()

        for coluna, nome in SERIES_DIARIAS.items():
            fig.add_trace(
                go.Scatter(
                    x=periodo["data"],
                    y=base_100(periodo[coluna]),
                    name=nome,
                    mode="lines",
                    line=dict(color=CORES[nome]),
                    legendrank=ORDEM_SERIES.index(nome),
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
                    legendrank=ORDEM_SERIES.index("IPCA"),
                    # O primeiro ponto fica na borda do eixo; sem isto, o marcador
                    # seria cortado ao meio.
                    cliponaxis=False,
                    customdata=pontos["rotulo"],
                    # O mês no texto evita confundir o ponto mensal com o valor
                    # do dia sob o cursor (a caixa unificada mostra o mais próximo).
                    hovertemplate="IPCA (%{customdata}): R$ %{y:.2f}<extra></extra>",
                )
            )
            nota_ipca = (
                "quanto os R$ 100 precisariam valer para manter o poder de compra, "
                "com a inflação desde o início do mês da data escolhida "
                f"(base: índice de {mes_base}); pontos nos fins de mês divulgados, "
                f"até {pontos['rotulo'].iloc[-1]}."
            )
        else:
            nota_ipca = (
                "ainda não há mês divulgado a partir de "
                f"{rotulo_mes(inicio_real.to_period('M'))}, por isso não aparece."
            )

        fig.update_layout(
            yaxis_title="R$",
            hovermode="x unified",  # uma caixa com todas as séries na mesma data
            xaxis_hoverformat="%d/%m/%Y",
            **layout_grafico(inicio_real, fim_real),
        )
        st.plotly_chart(fig)

        # O título saiu do gráfico; a data real de início fica nas notas.
        dia_util_seguinte = (
            " (o primeiro dia com dado a partir da data escolhida)"
            if inicio_real.date() != inicio
            else ""
        )
        notas = [
            f"**Período:** de {inicio_real:%d/%m/%Y}{dia_util_seguinte} até "
            f"{fim_real:%d/%m/%Y} (a última data em que CDI, Ibovespa e dólar têm dado).",
            "**CDI:** 100% do CDI, bruto de impostos. Na prática, há IR pela tabela "
            "regressiva, de 22,5% a 15% conforme o prazo, exceto em aplicações isentas "
            "para pessoa física, como LCI e LCA.",
            f"**IPCA:** {nota_ipca}",
            "**Ibovespa:** índice de retorno total (já inclui dividendos e outros "
            "proventos reinvestidos), nominal em reais e bruto de impostos e custos.",
            "**Dólar:** variação da PTAX venda, como dólar parado, sem rendimento. A "
            "PTAX é uma taxa de referência calculada pelo Banco Central e usada por "
            "empresas e contratos, não a cotação para comprar dólar.",
        ]
        with st.expander(ROTULO_NOTAS):
            st.markdown("\n".join(f"- {linha}" for linha in notas))

# --- Direita: ganhou da inflação? (juro real em 12 meses) ------------------------

with col_dir:
    st.markdown("#### Ganhou da inflação?")

    # Período completo: cada ponto é uma janela de 12 meses e não depende da data
    # de início escolhida ao lado. Só meses com CDI e IPCA (um último mês só com o
    # CDI fica de fora) e a partir do início da análise.
    real = mensal.dropna(subset=["juro_real_12m"])
    real = real[real["mes"] >= pd.Timestamp(DATA_INICIO_ANALISE).to_period("M")]

    if len(real) < 2:
        st.warning(
            "Há menos de dois meses com CDI e IPCA em 12 meses; o gráfico do juro "
            "real não é desenhado."
        )
    else:
        # Cada mês no último dia dele, como os pontos do IPCA no gráfico ao lado.
        datas_real = [m.end_time.normalize() for m in real["mes"]]
        y_min, y_max = faixa_eixo_y(real["juro_real_12m"])

        fig_real = go.Figure()
        fig_real.add_trace(
            go.Scatter(
                x=datas_real,
                y=real["juro_real_12m"],
                name="Juro real em 12 meses",
                mode="lines+markers",
                line=dict(color=COR_JURO_REAL, width=2.5),
                marker=dict(size=5),
                cliponaxis=False,
                showlegend=False,
                # Os componentes do mês, para ver se o movimento veio do juro ou
                # da inflação.
                customdata=real[["cdi_12m", "ipca_12m"]].to_numpy(),
                hovertemplate=(
                    "Juro real: %{y:.2f}%<br>"
                    "CDI 12m: %{customdata[0]:.2f}%<br>"
                    "IPCA 12m: %{customdata[1]:.2f}%<extra></extra>"
                ),
            )
        )

        # Faixa suave abaixo do zero (perdeu poder de compra) e a linha do empate.
        fig_real.add_hrect(
            y0=y_min, y1=0, fillcolor=COR_FAIXA_NEGATIVA, line_width=0, layer="below"
        )
        fig_real.add_hline(
            y=0,
            line_dash="dash",
            line_width=1,
            line_color=COR_JURO_REAL,
            annotation_text="empate com a inflação",
            annotation_position="bottom right",
        )

        fig_real.update_layout(
            yaxis_title="Juro real em 12 meses (%)",
            yaxis_range=[y_min, y_max],
            yaxis_ticksuffix="%",
            hovermode="x unified",
            xaxis_hoverformat="%m/%Y",
            **layout_grafico(datas_real[0], datas_real[-1]),
        )
        st.plotly_chart(fig_real)

        with st.expander(ROTULO_NOTAS):
            st.markdown(
                f"- **Período:** de {rotulo_mes(real['mes'].iloc[0])} a "
                f"{rotulo_mes(real['mes'].iloc[-1])}.\n"
                "- **Juro real em 12 meses:** quanto 100% do CDI ganhou (acima do "
                "zero) ou perdeu (abaixo) de poder de compra nos 12 meses até cada "
                "mês, calculado por (1 + CDI) ÷ (1 + IPCA) − 1. Bruto de IR: depois "
                "do imposto, o ganho real é menor. Mostra o período completo, até o "
                "último mês com IPCA divulgado, e não depende da data de início ao lado."
            )
