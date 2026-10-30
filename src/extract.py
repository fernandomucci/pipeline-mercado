"""Extração: baixa as séries das fontes e grava em data/raw sem tratamento."""

from datetime import date, timedelta

import pandas as pd
import requests

from src.config import (
    DATA_INICIO_EXTRACAO,
    DIR_RAW,
    SERIES_SGS,
    SGS_URL,
    TIMEOUT_REQUISICAO,
)

def data_fim_padrao() -> date:
    """Último dia considerado: ontem, para não pegar valor parcial do dia."""
    return date.today() - timedelta(days=1)

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
    """Baixa a série nome de SERIES_SGS e grava em data/raw/<nome>.csv."""
    fim = fim or data_fim_padrao()
    df = baixar_serie_sgs(SERIES_SGS[nome], inicio, fim)

    DIR_RAW.mkdir(parents=True, exist_ok=True)
    caminho = DIR_RAW / f"{nome}.csv"
    df.to_csv(caminho, index=False)

    print(
        f"{nome}: {len(df)} linhas, de {df['data'].iloc[0]} "
        f"a {df['data'].iloc[-1]} -> {caminho}"
    )

if __name__ == "__main__":
    extrair_serie_sgs("cdi")