"""Extração: baixa as séries das fontes e grava em data/raw sem tratamento."""

from datetime import date, timedelta

import pandas as pd
import requests
import yfinance as yf

from src.config import (
    DATA_INICIO_EXTRACAO,
    DIR_RAW,
    SERIES_SGS,
    SGS_URL,
    TICKER_IBOVESPA,
    TIMEOUT_REQUISICAO,
)


def data_fim_padrao() -> date:
    """Último dia considerado: ontem, para não pegar valor parcial do dia."""
    return date.today() - timedelta(days=1)


# --- SGS (Banco Central) -------------------------------------------------------


def baixar_serie_sgs(codigo: int, inicio: date, fim: date) -> pd.DataFrame:
    """Baixa uma série do SGS e devolve as colunas como vieram da API (texto)."""
    # A API do SGS recusa consultas com mais de 10 anos entre as datas.
    if fim > inicio.replace(year=inicio.year + 10):
        raise ValueError("A API do SGS aceita no máximo 10 anos por consulta.")

    resposta = requests.get(
        SGS_URL.format(codigo=codigo),
        params={
            "formato": "json",
            "dataInicial": inicio.strftime("%d/%m/%Y"),
            "dataFinal": fim.strftime("%d/%m/%Y"),
        },
        timeout=TIMEOUT_REQUISICAO,
    )
    resposta.raise_for_status()

    registros = resposta.json()
    if not registros:
        raise ValueError(f"Série {codigo} sem dados entre {inicio} e {fim}.")

    df = pd.DataFrame(registros)
    colunas_esperadas = {"data", "valor"}
    if not colunas_esperadas.issubset(df.columns):
        raise ValueError(
            f"Série {codigo}: colunas inesperadas {list(df.columns)}; "
            f"esperava pelo menos {sorted(colunas_esperadas)}."
        )
    return df


def extrair_serie_sgs(
    nome: str,
    inicio: date = DATA_INICIO_EXTRACAO,
    fim: date | None = None,
) -> None:
    """Baixa a série `nome` de SERIES_SGS e grava em data/raw/<nome>.csv."""
    fim = fim or data_fim_padrao()
    df = baixar_serie_sgs(SERIES_SGS[nome], inicio, fim)

    DIR_RAW.mkdir(parents=True, exist_ok=True)
    caminho = DIR_RAW / f"{nome}.csv"
    df.to_csv(caminho, index=False)

    print(
        f"{nome}: {len(df)} linhas, de {df['data'].iloc[0]} "
        f"a {df['data'].iloc[-1]} -> {caminho}"
    )


# --- yfinance (Ibovespa) -------------------------------------------------------


def baixar_ibovespa(inicio: date, fim: date) -> pd.DataFrame:
    """Baixa o Ibovespa diário pelo yfinance, como veio (datas com fuso horário).

    `fim` é inclusivo, como no SGS. O yfinance trata o fim como exclusivo,
    por isso o pedido vai até o dia seguinte.
    """
    # Ticker.history devolve colunas de um nível só para um único ticker.
    df = yf.Ticker(TICKER_IBOVESPA).history(
        start=inicio,
        end=fim + timedelta(days=1),
        interval="1d",
        auto_adjust=False,  # explícito: não depender do padrão da versão
    )

    # O yfinance pode devolver uma tabela vazia só com um aviso, sem erro.
    if df.empty:
        raise ValueError(
            f"{TICKER_IBOVESPA}: o yfinance não devolveu dados entre {inicio} e {fim}."
        )
    if "Close" not in df.columns:
        raise ValueError(
            f"{TICKER_IBOVESPA}: coluna Close ausente; colunas recebidas: "
            f"{list(df.columns)}."
        )

    # A data sai do índice e vira coluna, ainda com o fuso original.
    return df.reset_index()


def extrair_ibovespa(
    inicio: date = DATA_INICIO_EXTRACAO,
    fim: date | None = None,
) -> None:
    """Baixa o Ibovespa e grava em data/raw/ibov.csv, sem tratamento."""
    fim = fim or data_fim_padrao()
    df = baixar_ibovespa(inicio, fim)

    DIR_RAW.mkdir(parents=True, exist_ok=True)
    caminho = DIR_RAW / "ibov.csv"
    df.to_csv(caminho, index=False)

    datas = df.iloc[:, 0]
    print(
        f"ibov: {len(df)} linhas, de {datas.iloc[0]:%d/%m/%Y} "
        f"a {datas.iloc[-1]:%d/%m/%Y} -> {caminho}"
    )


if __name__ == "__main__":
    for nome in SERIES_SGS:
        extrair_serie_sgs(nome)
    extrair_ibovespa()
