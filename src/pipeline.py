"""Executa o pipeline: extração -> transformação -> validação -> carga."""

from src.config import ARQUIVO_DIARIO, ARQUIVO_MENSAL, SERIES_SGS
from src.extract import extrair_serie_sgs
from src.load import salvar_csv
from src.transform import montar_diario, montar_mensal
from src.validate import validar_cdi_mensal, validar_ipca_12m


def main() -> None:
    for nome in SERIES_SGS:
        extrair_serie_sgs(nome)

    diario = montar_diario()
    mensal = montar_mensal()

    # Se alguma validação reprovar, nenhum arquivo processado é gravado.
    validar_cdi_mensal(diario)
    validar_ipca_12m(mensal)

    # Gravados juntos: os dois arquivos sempre vêm da mesma execução.
    salvar_csv(diario, ARQUIVO_DIARIO)
    salvar_csv(mensal, ARQUIVO_MENSAL)


if __name__ == "__main__":
    main()
