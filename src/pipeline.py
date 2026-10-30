"""Executa o pipeline: extração -> transformação -> validação -> carga."""

from src.config import ARQUIVO_DIARIO
from src.extract import extrair_serie_sgs
from src.load import salvar_csv
from src.transform import montar_diario
from src.validate import validar_cdi_mensal


def main() -> None:
    extrair_serie_sgs("cdi")
    diario = montar_diario()
    validar_cdi_mensal(diario)  # se reprovar, para antes de gravar
    salvar_csv(diario, ARQUIVO_DIARIO)


if __name__ == "__main__":
    main()
