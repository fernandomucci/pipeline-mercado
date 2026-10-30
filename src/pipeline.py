"""Executa o pipeline: extração -> transformação -> carga."""

from src.config import ARQUIVO_DIARIO
from src.extract import extrair_serie_sgs
from src.load import salvar_csv
from src.transform import montar_diario


def main() -> None:
    extrair_serie_sgs("cdi")
    salvar_csv(montar_diario(), ARQUIVO_DIARIO)


if __name__ == "__main__":
    main()
