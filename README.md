# pipeline-mercado

Pipeline ETL em Python que coleta quatro indicadores do mercado financeiro brasileiro em fontes públicas (CDI, IPCA, dólar PTAX e Ibovespa), trata e valida os dados contra fontes oficiais, grava tudo em CSVs organizados e alimenta um dashboard em Streamlit.

> Case técnico do processo seletivo da Vêneto Family Office (2026). O uso de IA no desenvolvimento está descrito em [IA.md](IA.md).

---

## Sumário

1. [O que o pipeline faz](#o-que-o-pipeline-faz)
2. [Como executar do zero](#como-executar-do-zero)
3. [O dashboard: para quem é e o que responde](#o-dashboard-para-quem-é-e-o-que-responde)
4. [Estrutura do repositório](#estrutura-do-repositório)
5. [Decisões (e por quê)](#decisões-e-por-quê)
6. [Validação: como os números foram conferidos](#validação-como-os-números-foram-conferidos)
7. [Limitações](#limitações)
8. [Melhorias futuras](#melhorias-futuras)
9. [Escopo: o que foi planejado e o que foi feito](#escopo-o-que-foi-planejado-e-o-que-foi-feito)
10. [Uso de IA](#uso-de-ia)

---

## O que o pipeline faz

| Indicador | Fonte | Frequência e unidade |
|---|---|---|
| CDI | SGS / Banco Central, série 12 | Diária (dias úteis), % ao dia |
| Dólar PTAX venda | SGS / Banco Central, série 1 | Diária (dias úteis), R$ por US$ |
| IPCA | SGS / Banco Central, série 433 | Mensal, variação % no mês |
| Ibovespa | Yahoo Finance via yfinance, ticker `^BVSP` | Diária (pregões), pontos |

O período de análise começa em **01/10/2021** (5 anos). A extração começa 12 meses antes, em 01/10/2020, porque os acumulados em 12 meses do primeiro mês da análise precisam dos 12 meses anteriores. Os dados vão até o dia anterior à execução.

Cada execução faz, nesta ordem:

```
Extração      SGS (CDI, PTAX, IPCA) + yfinance (Ibovespa)  →  data/raw/
Transformação datas e tipos, calendários, índices, acumulados e juro real
Validação     CDI x SGS 4391 · IPCA 12m x IBGE · Ibovespa x B3
Carga         data/processed/diario.csv e mensal.csv
```

**Se qualquer validação reprovar, nenhum arquivo processado é gravado**, e os arquivos da execução anterior continuam valendo.

**As tabelas geradas:**

| Arquivo | Uma linha por | Colunas |
|---|---|---|
| `diario.csv` | dia útil | `data`, `cdi_taxa_ano`, `cdi_indice`, `dolar`, `ibov` |
| `mensal.csv` | mês | `mes`, `ipca_mes`, `ipca_indice`, `ipca_12m`, `cdi_mes`, `cdi_12m`, `juro_real_12m` |

---

## Como executar do zero

**Pré-requisitos:** Python 3.11 ou mais novo (testado com 3.11.9), Git e acesso à internet.

### 1. Clonar e criar o ambiente

No Windows (PowerShell):

```powershell
git clone https://github.com/fernandomucci/pipeline-mercado.git
cd pipeline-mercado
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Se o PowerShell recusar a ativação do venv, rode antes `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned` (vale só para aquela janela).

No macOS ou Linux:

```bash
git clone https://github.com/fernandomucci/pipeline-mercado.git
cd pipeline-mercado
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### 2. Abrir o dashboard

```
streamlit run app.py
```

O dashboard abre no navegador (normalmente em `http://localhost:8501`). Os arquivos de `data/processed` já estão no repositório, então ele funciona sem rodar o pipeline.

### 3. Atualizar os dados (opcional)

```
python -m src.pipeline
```

Baixa as quatro séries até ontem, valida e regrava `data/raw` e `data/processed`. A saída mostra cada etapa: linhas extraídas por série, a correção aplicada no Ibovespa, o relatório de calendários e o resultado das três validações.

Para conferir os arquivos já gravados sem baixar tudo de novo:

```
python -m src.validate
```

**Se aparecer um erro de timeout** (`api.bcb.gov.br ... Read timed out`), é a API do Banco Central demorando a responder. O pipeline para antes de gravar; basta rodar de novo depois de alguns minutos.

---

## O dashboard: para quem é e o que responde

**Para quem:** a equipe de Inteligência Comercial e os assessores, que usam esses indicadores para embasar conversas com clientes. O cenário pensado é o assessor que abre a tela alguns minutos antes de uma ligação e quer responder "como estão os investimentos e a economia?".

O dashboard entrega **réguas de referência, cada uma com a sua data**. Ele não mostra a carteira de nenhum cliente: comparar a carteira com essas réguas é trabalho do assessor.

### As três perguntas e onde cada uma é respondida

**1. Como estão os indicadores hoje, e de quando é cada dado?**
Quatro cartões no topo: CDI ao ano, IPCA em 12 meses, Ibovespa e dólar PTAX. Cada cartão mostra a data do próprio dado, porque as séries não terminam no mesmo dia: o IPCA sai com cerca de um mês de atraso, e o CDI de um dia só é publicado no dia seguinte. O cartão do IPCA mostra a meta de inflação (3%, intervalo de 1,5% a 4,5%), porque sem ela o número fica solto. O "?" de cada cartão explica o indicador.

**2. Quanto R$ 100 aplicados numa data viraram no CDI, no Ibovespa e no dólar, e quanto precisariam ter virado só para acompanhar a inflação?**
Gráfico em base 100, à esquerda, com a data inicial escolhível ("Quanto R$ 100 viraram desde [data]"). Responde a "renda fixa ou bolsa?" e "o dólar subiu muito?" para qualquer período. A linha do IPCA funciona como a linha mínima: acima dela, o dinheiro ganhou poder de compra.

**3. A renda fixa de referência (100% do CDI) ganhou da inflação em cada janela de 12 meses, e por quanto?**
Gráfico do juro real em 12 meses, à direita, com uma linha no zero marcando o empate com a inflação e uma faixa suave na região abaixo do zero (perdeu poder de compra). A caixa do mouse mostra também o CDI e o IPCA em 12 meses de cada mês, para ver se o movimento veio do juro ou da inflação.

### Por que essas visualizações

- **Poucos elementos, cada um respondendo a uma pergunta.** O case pede "menos é mais", e o assessor tem poucos minutos.
- **Base 100** coloca séries de naturezas diferentes (taxa, índice, cotação) na mesma unidade: reais a partir de R$ 100. Sem isso, não dá para comparar CDI, Ibovespa e dólar no mesmo gráfico.
- **Juro real numa linha só, e não CDI e IPCA em duas linhas.** Com duas linhas, o olho mede a distância entre elas, e essa distância é a subtração, que erra (veja [juro real](#juro-real-divisão-e-não-subtração)). O gráfico mostra a conta certa.
- **Dois gráficos lado a lado, com o seletor de data dentro da coluna do primeiro**, para ficar claro que a data só vale para ele. O juro real mostra sempre o período todo, porque cada ponto já é uma janela de 12 meses e não depende de data inicial.
- **As ressalvas ficam a um clique** ("Notas (valores brutos de impostos)"), com a principal visível no próprio rótulo.

---

## Estrutura do repositório

```
pipeline-mercado/
├── README.md
├── IA.md                 # relatórios de uso de IA (duas conversas)
├── requirements.txt      # versões fixas
├── app.py                # dashboard Streamlit; só lê data/processed
├── src/
│   ├── __init__.py
│   ├── config.py         # códigos das séries, período e caminhos (só valores)
│   ├── extract.py        # API do SGS + yfinance -> data/raw
│   ├── transform.py      # leitura e checagens do raw, calendários, tabelas diária e mensal
│   ├── indicadores.py    # funções de cálculo puras (índices, acumulados, juro real)
│   ├── validate.py       # confere os resultados contra valores oficiais
│   ├── load.py           # grava data/processed
│   └── pipeline.py       # extração -> transformação -> validação -> carga
└── data/
    ├── raw/              # cdi.csv, ptax.csv, ipca.csv, ibov.csv, como vieram das fontes
    └── processed/        # diario.csv e mensal.csv
```

---

## Decisões (e por quê)

### Fontes e séries

| Decisão | Escolha | Por quê |
|---|---|---|
| CDI | Série 12 (% ao dia), e não a 4389 (% ao ano) | A taxa diária permite montar o índice acumulado dia a dia. A taxa ao ano do cartão é calculada a partir dela |
| Dólar | PTAX venda (série 1) | Taxa de referência oficial do Banco Central, publicada todo dia útil |
| Ibovespa | `yf.Ticker("^BVSP").history(...)`, coluna `Close`, `auto_adjust=False` | O case pede o yfinance. Para um ticker só, o `history` devolve colunas simples (o `yf.download` devolve dois níveis). O Ibovespa já é um índice de retorno total (inclui dividendos), então o fechamento é o valor certo para comparar com o CDI |
| Acesso ao SGS | `requests` direto na API, com timeout e checagem de resposta vazia | Sem dependências a mais; o pipeline para com mensagem clara se a fonte mudar |
| Versões | Fixadas no `requirements.txt`, incluindo o `curl_cffi` | O `curl_cffi` é dependência do yfinance, e uma versão nova dele já quebrou o yfinance. Fixar evita que o projeto pare sozinho |

### Armazenamento

| Decisão | Escolha | Por quê |
|---|---|---|
| Formato | CSV | As tabelas têm cerca de 1.500 linhas. CSV abre em qualquer ferramenta e é legível no próprio GitHub |
| Camadas | `data/raw` (como veio da fonte) e `data/processed` (tratado) | O raw prova o que a fonte entregou; o processed é o que o dashboard lê |
| Dados no repositório | Os CSVs são commitados | O dashboard abre sem depender da API, e o histórico mostra o que mudou a cada atualização |
| Datas nos arquivos | Padrão ISO (`2026-10-29`); o mês como `2026-09` | Sem ambiguidade entre dia e mês e com ordenação correta. O formato brasileiro aparece só na tela |

### Calendários e dias sem dado

| Decisão | Escolha | Por quê |
|---|---|---|
| Juntar as séries diárias | União das datas: nenhuma data de nenhuma série é descartada | Cada série tem o próprio calendário (a bolsa e os bancos não fecham nos mesmos dias) |
| Dias sem dado de uma série | Repetir o último valor, **só entre datas reais** (`ffill(limit_area="inside")`), e só para níveis (índice do CDI, dólar, Ibovespa) | Bolsa fechada = índice parado. A taxa do CDI nunca é repetida: uma taxa pertence a um dia |
| Fim das séries | Cada série vai até o próprio último dado, sem inventar valor | As fontes publicam em horários diferentes (o CDI de um dia só sai no dia seguinte). Repetir o CDI de quinta numa sexta útil seria errado, porque o CDI rendeu na sexta |
| Gráfico comparativo | Usa só as datas em que CDI, Ibovespa e dólar têm dado | As três linhas comparam exatamente o mesmo período |
| Relatório de calendários | A cada execução, lista os dias em que uma série falta dentro do próprio período | Conferência de qualidade. CDI e PTAX têm calendários idênticos; o Ibovespa falta em 13 dias, todos explicados (ver [validação](#validação-como-os-números-foram-conferidos)) |

### CDI

- **Convenção D-1.** A taxa registrada num dia remunera daquele dia até o dia útil seguinte. Por isso o índice de cada dia inclui as taxas até o dia anterior: `fator.shift(1, fill_value=1.0).cumprod()`. Assim, o CDI e o Ibovespa medem o mesmo intervalo no gráfico de base 100. A validação mensal confirmou a convenção: com a janela deslocada em um dia, os meses de alta da Selic (out e dez/2021) reprovariam.
- **Juros compostos:** o índice multiplica os fatores diários (1 + taxa), não soma as taxas.
- **Taxa ao ano do cartão:** `(1 + taxa diária) ^ 252 − 1`, a convenção brasileira de 252 dias úteis.
- **CDI no mês:** razão entre o índice do primeiro dia útil do mês seguinte e o do primeiro dia útil do mês. Só entram meses fechados: o mês corrente fica de fora até existir um dia do mês seguinte.
- **CDI em 12 meses:** os meses viram um índice e entra a mesma função do IPCA, para as duas janelas serem idênticas.

### IPCA

- **O mês é um período, não um dia.** O SGS data cada mês no dia 01, mas o IPCA de setembro é do mês inteiro. Na memória, o mês é um `Period`; no arquivo, `2026-09`.
- **O índice inclui o próprio mês** (sem a D-1 do CDI): a inflação de setembro acontece durante setembro.
- **IPCA em 12 meses** = índice do mês ÷ índice de 12 meses antes − 1. Os 12 primeiros meses da extração ficam vazios, e é para isso que existe a folga de 12 meses.
- **Checagens na leitura:** toda data no dia 01 e nenhum mês faltando. "12 linhas antes" só significa "12 meses antes" se não houver buraco.
- **Meses ainda não divulgados não aparecem**, nem vazios nem estimados.

### Ibovespa

- **Fuso horário.** O raw guarda a data como o yfinance entrega (`2020-10-01 00:00:00-03:00`). Na leitura, o fuso é removido **sem converter** a hora, e o pipeline para se alguma hora não for 00:00. Converter o fuso poderia jogar um fechamento para o dia anterior.
- **Checagens:** sem datas repetidas, em ordem, sem fins de semana e sem fechamento vazio ou ≤ 0.
- **Correção de um erro do Yahoo.** Em 29/12/2022, o Yahoo tem 110.031 pontos; a B3 publicou 109.734,60 (queda de 0,46% no dia, contra 0,19% no Yahoo). A correção fica num registro no código (`CORRECOES_IBOV`), com a fonte e a data da conferência, e vale só no `processed`: o raw continua com o valor do Yahoo, e o pipeline avisa a correção a cada execução. Deixar o valor errado mostraria um número sabidamente falso; repetir o dia anterior ficaria ainda mais longe do oficial.

### Juro real: divisão, e não subtração

```
juro real = (1 + CDI 12m) ÷ (1 + IPCA 12m) − 1
```

A subtração (CDI − IPCA) superestima o ganho. Exemplo: R$ 100 viram R$ 120 (CDI de 20%), e uma cesta que custava R$ 100 passa a custar R$ 110 (inflação de 10%). Com R$ 120 compram-se 120 ÷ 110 = 1,0909 cestas: o poder de compra subiu **9,09%**, e não 10%.

**Exemplo resolvido com os dados reais (dez/2021):**

| | Valor |
|---|---|
| CDI em 12 meses | 4,42% (igual ao CDI acumulado de 2021) |
| IPCA em 12 meses | 10,06% (IBGE) |
| Juro real | (1 + 0,0442) ÷ 1,1006 − 1 = **−5,12%** |
| Pela subtração, daria | 4,42 − 10,06 = −5,64% |

Em 2021, o CDI perdeu 5,1% de poder de compra. Em set/2026, com CDI de 14,47% e IPCA de 4,58% em 12 meses, o juro real é de **+9,46%**.

Quando o CDI de um mês já fechou e o IPCA ainda não foi divulgado (por uns dez dias de cada mês), a linha desse mês fica só com o CDI, e o juro real fica vazio.

### Dashboard

| Decisão | Escolha | Por quê |
|---|---|---|
| Base do IPCA no gráfico de R$ 100 | O índice do mês **anterior** ao mês de início | Para 01/10/2021, a base é set/2021, e a inflação de outubro conta. Num início no meio do mês, o mês inteiro conta: superestima um pouco a inflação, o lado prudente (erra contra o CDI, não a favor). Calcular proporcional aos dias seria inventar inflação de meio mês |
| Pontos do IPCA | Uma bolinha no último dia de cada mês divulgado, ligadas por linha reta; o mês aparece na caixa do mouse | As bolinhas mostram onde está o dado real; o mês no texto evita confundir o ponto mensal com o valor do dia |
| Seletor de data | Com aviso quando o período tem menos de 2 dias com dado | Não esconde nenhuma data válida e não depende de um limite arbitrário |
| Cores | Paleta Okabe-Ito, fixa por série (CDI azul, IPCA rosa, Ibovespa vermelho-alaranjado, dólar verde); juro real em cinza | Distinguível por quem tem daltonismo; as cores não mudam quando uma série entra ou sai. O juro real é uma conta derivada, não uma das quatro séries |
| Região abaixo do zero no juro real | Faixa cinza suave, e não verde/vermelho | Verde e vermelho é o par que mais confunde quem tem daltonismo |
| Eixo de datas | Intervalo definido à mão, do primeiro ao último dado | Com marcadores, o Plotly deixa 5% de folga nas pontas, e o eixo ia até 01/2027 |
| Cartão do Ibovespa | Pontos inteiros, sem decimais | O Yahoo entrega inteiros; casas decimais sugeririam uma precisão que o dado não tem |
| Meta de inflação | Constante no `app.py` (centro, piso e teto), com a fonte (CMN) | A meta contínua de 3% vale desde 2025 e só muda com 36 meses de antecedência |
| Textos de ressalva | CDI e Ibovespa brutos de IR; tabela regressiva (22,5% a 15%), exceto isentos para pessoa física, como LCI e LCA; PTAX como taxa de referência, e não a cotação para comprar dólar | Pontos levantados com o profissional da área financeira consultado |

---

## Validação: como os números foram conferidos

### Validações automáticas (rodam a cada execução)

| O que | Contra | Tolerância | Resultado em 01/11/2026 |
|---|---|---|---|
| CDI no mês | SGS série 4391 (CDI acumulado no mês, 2 casas) | 0,005 p.p.: meia unidade da 2ª casa, porque só a referência vem arredondada | 72 de 72 meses (out/2020 a set/2026); maior diferença 0,0050 p.p. em fev/2022 |
| IPCA em 12 meses | IBGE: dezembros de 2021 a 2025 (10,06; 5,79; 4,62; 4,83; 4,26) e set/2026 (4,58) | Calculada por mês, pelo pior caso do arredondamento (0,068 a 0,071 p.p.): cada um dos 12 meses já vem com 2 casas | 6 de 6; maior diferença 0,0052 p.p. em dez/2022 (tolerância 0,0682) |
| Ibovespa | B3: último pregão de 2021 a 2025 | 1 ponto: o Yahoo entrega inteiros, e tirar os centavos erra menos de 1 ponto | 4 de 4 (maior diferença 0,44 ponto) e a divergência conhecida de 29/12/2022 |

A validação do Ibovespa compara o **dado original do Yahoo**, antes da correção. Se comparasse o valor corrigido com a mesma B3 que o corrigiu, passaria sempre. Se um dia o Yahoo consertar o dado, o pipeline avisa que a correção ficou obsoleta.

### Conferências feitas à mão

- O raw do CDI tem 1.526 linhas, exatamente os dias úteis bancários de 01/10/2020 a 29/10/2026.
- O primeiro valor do CDI (0,007469% ao dia, cerca de 1,9% ao ano) é coerente com a Selic de 2% em out/2020.
- IPCA mensal: out/2020 = 0,86; nov/2020 = 0,89; ago/2026 = −0,32 (deflação); set/2026 = 0,82, todos iguais aos do IBGE.
- O CDI em 12 meses de dez/2021 (4,42%) bate com o CDI acumulado de 2021.
- Os 13 dias sem pregão do Ibovespa têm explicação: 3 feriados de São Paulo antes de 2022, quando a B3 passou a abrir neles (20/11/2020, 25/01/2021, 09/07/2021); 8 dias de 24 e 31/12, em que a B3 não abre (2020, 2021, 2024, 2025); e 2 últimos dias úteis do ano sem pregão (30/12/2022 e 29/12/2023).
- **O salto de 26/10/2026 é real.** No primeiro pregão após o 2º turno das eleições, o Ibovespa caiu 13,88% e a PTAX subiu 9,2%. Os valores foram conferidos em notícias (fechamento do Ibovespa: 176.608,23 pontos). A PTAX subiu mais que o dólar comercial de fechamento (+8,21%) porque mede outro horário: é a média das consultas do Banco Central entre 10h e 13h, e não o fechamento do dia.

---

## Limitações

**Dados**

- **Ibovespa conferido em só 5 dias.** Os fechamentos do Yahoo são conferidos apenas nos cinco pontos de referência da B3, e um erro em outro dia pode passar despercebido. Foi testada uma conferência automática que comparava o fechamento de cada pregão com a abertura do pregão seguinte no próprio Yahoo. O teste foi descartado porque a abertura do Yahoo não repete o fechamento anterior (em 1.513 pares, só 440 eram iguais e 763 diferiam em mais de 1 ponto), então essa diferença não indica erro.
- **Uma correção manual.** O fechamento de 29/12/2022 é um valor digitado a partir da B3, documentado no código.
- **O Yahoo Finance não é uma fonte oficial**, e entrega o Ibovespa em pontos inteiros.
- **PTAX e CDI ao ano sem validação automática.** A PTAX vem direto do Banco Central, sem cálculo, e foi conferida à mão no início e no fim. A taxa ao ano do cartão poderia ser conferida contra a série 4389, que ficou fora do escopo.
- **Juro real validado de forma indireta:** seus dois componentes são validados, e um mês (dez/2021) foi conferido à mão. Não existe série oficial de "CDI real" para comparar.
- **Tolerâncias apoiadas em arredondamento.** No CDI, a maior diferença (fev/2022) ficou na borda da tolerância, por puro arredondamento (0,75504 contra 0,76 publicado). A tolerância do IPCA supõe que o IBGE calcula o acumulado a partir do número-índice e só depois arredonda.
- **A meta de inflação é uma constante** no código e precisa ser atualizada à mão se o CMN mudá-la.

**Execução**

- **Depende de internet a cada execução:** o pipeline baixa todas as séries e a validação baixa a série 4391. Sem rede, nada é gravado.
- **Sem atualização incremental** (o bônus do case): toda execução baixa o período inteiro.
- **Sem nova tentativa automática** quando a API demora. O timeout do Banco Central aconteceu durante o desenvolvimento; o pipeline parou antes de gravar, como esperado, e bastou rodar de novo.
- **"Até ontem" usa a data do computador** em que o pipeline roda.
- **Aviso `Pandas4Warning` na saída.** Ele vem de dentro do yfinance (uso de `inplace` no `sort_index`, marcado para remoção num pandas futuro). Não afeta o resultado e foi deixado visível em vez de silenciado; com as versões fixadas, nada muda sozinho.
- **Sem testes automatizados** (pytest). As funções de cálculo ficam em `indicadores.py`, separadas de leitura e gravação, justamente para poderem ser testadas isoladamente.

**Leitura dos números**

- **Valores nominais e brutos.** CDI e Ibovespa não descontam IR, taxas nem custos; o juro real também é bruto de IR.
- **Base do IPCA no meio do mês.** Num início no meio do mês, a linha do IPCA conta a inflação do mês inteiro (escolha conservadora).
- **O dashboard foi pensado para tela de computador.** Em celular, as colunas se empilham sozinhas, mas a altura dos gráficos é fixa (`ALTURA_GRAFICOS`).

---

## Melhorias futuras

- **Rentabilidade em 1, 3 e 5 anos (bloco B):** uma tabela com quanto cada série rendeu nessas janelas. Hoje a mesma resposta sai do gráfico "Quanto R$ 100 viraram", escolhendo a data de início. A tabela ficou de fora para priorizar a validação dos dados e a reprodutibilidade no prazo. Um cuidado para quando for feita: o IPCA termina num mês diferente das séries diárias, então "1 ano" do IPCA e "1 ano" do CDI não são a mesma janela, e isso precisa aparecer na tabela. Os botões de período do próprio Plotly não servem para isso, porque só dão zoom e não recalculam a base 100.
- **Atualização incremental:** baixar só os dados novos a cada execução.
- **Novas tentativas automáticas** quando a API demora, antes de desistir.
- **Conferir mais dias do Ibovespa** contra o histórico completo da B3.
- **Validar a taxa ao ano do CDI** contra a série 4389.
- **Testes automatizados** das funções de `indicadores.py`.

---

## Escopo: o que foi planejado e o que foi feito

| Bloco | Conteúdo | Status |
|---|---|---|
| A | Cartões com a situação atual, cada um com a sua data | Feito |
| B | Rentabilidade por janela (1, 3 e 5 anos) | Melhoria futura |
| C | Base 100 com data inicial escolhível: CDI, Ibovespa, dólar e IPCA | Feito |
| D | IPCA em 12 meses com a faixa da meta | Cortado como gráfico; a meta atual aparece no cartão do IPCA |
| E | Juro real em 12 meses, com a linha de empate |Feito (originalmente CDI 12m × IPCA 12m em duas linhas; trocado após a consulta ao profissional da área) |
 
**Por que o bloco D foi cortado:** o gráfico do IPCA em 12 meses com a faixa da meta exigiria a meta de cada mês do período, que não está em nenhuma das fontes e mudou de regime em 2025 (até 2024, havia uma meta diferente para cada ano-calendário). Em vez disso, o cartão do IPCA mostra a meta atual como referência, definida como uma constante única no código, com a fonte (CMN).

---

## Uso de IA

O desenvolvimento usou IA (Claude), para escrever o código, etapa por etapa, para revisar o código e as explicações, montar os pedidos e organizar a documentação. O relatório da conversas, gerado pela própria IA com o prompt do case e salvos sem edição, estão em [IA.md](IA.md).
