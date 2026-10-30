"""Configurações do pipeline: apenas valores fixos usados pelas etapas.

Nenhuma lógica de extração, tratamento ou exibição mora aqui.
"""

from datetime import date
from pathlib import Path

# --- Fontes ------------------------------------------------------------------

# API do SGS (Banco Central). {codigo} é substituído pelo código da série;
# formato e datas são passados como parâmetros da requisição no extract.
SGS_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"

TIMEOUT_REQUISICAO = 30

# Séries do SGS usadas no pipeline (nome -> código).
# O nome vira o nome do arquivo em data/raw (ex.: cdi.csv).
SERIES_SGS = {
    "cdi": 12,    # Taxa de juros - CDI | % ao dia | diária (dias úteis)
    "ptax": 1,    # Dólar americano, venda (PTAX) | R$/US$ | diária (dias úteis)
    "ipca": 433,  # IPCA | variação % no mês | mensal
}

# Série usada só na validação: CDI acumulado no mês | % ao mês | mensal. Nao aparece no dashboard
SERIE_VALIDACAO_CDI_MES = 4391

# Ibovespa via yfinance.
TICKER_IBOVESPA = "^BVSP"

# --- Período -----------------------------------------------------------------

# Início da análise: dia 1 de um mês, para a tabela mensal não começar com
# um mês pela metade.
DATA_INICIO_ANALISE = date(2021, 10, 1)

# Folga de 12 meses: os acumulados em 12 meses do primeiro mês da análise
# precisam dos 12 meses anteriores. Derivada da data de análise para que
# mudar uma data ajuste a outra.
DATA_INICIO_EXTRACAO = DATA_INICIO_ANALISE.replace(year=DATA_INICIO_ANALISE.year - 1)

# A data final ("ontem") não fica aqui: depende do dia em que o pipeline roda,
# então é calculada no momento da extração.

# --- Caminhos ----------------------------------------------------------------

# Raiz do projeto calculada a partir deste arquivo (src/config.py), para que
# os caminhos funcionem de qualquer pasta em que o comando for executado.
RAIZ_PROJETO = Path(__file__).resolve().parent.parent
DIR_RAW = RAIZ_PROJETO / "data" / "raw"
DIR_PROCESSED = RAIZ_PROJETO / "data" / "processed"
