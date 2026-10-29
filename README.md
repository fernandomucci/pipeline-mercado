# pipeline-mercado

Pipeline ETL em Python que coleta indicadores do mercado financeiro brasileiro em fontes públicas, trata os dados, organiza tudo em uma base em CSV e alimenta um dashboard em Streamlit.

> **Status:** em construção. Case técnico do processo seletivo da Vêneto Family Office.

## Objetivo

Substituir o acompanhamento manual de quatro indicadores de mercado por um pipeline reprodutível, cobrindo os últimos 5 anos:

| Indicador | Fonte | Frequência e unidade |
|---|---|---|
| CDI | SGS / Banco Central, série 12 | Diária (dias úteis), % ao dia |
| IPCA | SGS / Banco Central, série 433 | Mensal, variação % no mês |
| Dólar PTAX venda | SGS / Banco Central, série 1 | Diária (dias úteis), R$ por US$ |
| Ibovespa | yfinance, ticker `^BVSP` | Diária (pregões), pontos |

## Público

Equipe de Inteligência Comercial e assessores, que usam esses indicadores para embasar conversas com clientes.

O dashboard entrega **réguas de referência, cada uma com sua data**. Ele não mostra a carteira de nenhum cliente: a comparação entre a carteira de cada cliente e essas réguas é feita pelo assessor.

## Perguntas que o dashboard responde

1. **Como estão os indicadores hoje, e de quando é cada dado?**
   O IPCA é divulgado com cerca de um mês de defasagem em relação às outras séries, então a data de referência de cada número faz parte da resposta.

2. **Quanto R$ 100 aplicados em uma data viraram no CDI, no Ibovespa e no dólar, e quanto precisariam ter virado só para acompanhar a inflação?**
   Responde, para o período que o usuário escolher, perguntas como "valeu mais a pena a renda fixa ou a bolsa?" e "quanto o dólar subiu?".

3. **A renda fixa de referência (100% do CDI) está ganhando da inflação, e por quanto? A inflação está subindo ou caindo?**
   Comparação entre o CDI e o IPCA acumulados em 12 meses.

## Escopo

| Bloco | Conteúdo | Pergunta | Status |
|---|---|---|---|
| A | Cartões com a situação atual: CDI ao ano, IPCA em 12 meses, dólar e Ibovespa, cada um com sua data de referência | 1 | No escopo |
| B | Tabela de rentabilidade por janela (no mês, no ano, em 12 meses, no período) | 1 e 2 | Opcional, se houver tempo |
| C | Gráfico em base 100 com período escolhível: CDI, Ibovespa, dólar e IPCA | 2 | No escopo |
| D | IPCA em 12 meses com a faixa da meta de inflação | 3 | Cortado |
| E | CDI em 12 meses × IPCA em 12 meses; a distância entre as linhas é o juro real | 3 | No escopo |

**Por que o bloco D foi cortado:** a meta de inflação não está em nenhuma das fontes do pipeline. Exibi-la exigiria uma tabela mantida à mão com a meta de cada ano definida pelo Conselho Monetário Nacional. O bloco E já mostra se a inflação está subindo ou caindo. A consequência, assumida conscientemente, é que o dashboard não indica se a inflação está acima ou abaixo da meta, e, para caber no prazo, priorizei os blocos que respondem às perguntas principais.

## Estrutura (planejada)

```
pipeline-mercado/
├── README.md
├── IA.md
├── requirements.txt
├── .gitignore
├── app.py                # dashboard Streamlit; só lê data/processed
├── src/
│   ├── __init__.py
│   ├── config.py         # códigos das séries, período e caminhos
│   ├── extract.py        # API do SGS + yfinance → data/raw
│   ├── transform.py      # limpeza, índices acumulados, tabelas diária e mensal
│   ├── load.py           # grava data/processed
│   ├── indicadores.py    # funções de cálculo puras
│   ├── validate.py       # confere resultados contra valores oficiais
│   └── pipeline.py       # executa extração → transformação → carga → validação
└── data/
    ├── raw/              # dados como vieram das fontes
    └── processed/        # diario.csv e mensal.csv
```

Os arquivos são criados à medida que cada etapa é implementada.

## Como executar

_A preencher._

## Decisões

_A preencher._

## Limitações

_A preencher._
