# IA.md — Uso de IA no case pipeline-mercado

> Relatório gerado pelo Claude (assistente de IA da Anthropic; modelo configurado na sessão: `claude-opus-5-5`), a pedido do usuário, a partir do histórico completo da conversa de 28/10/2026 a 01/11/2026. O texto é escrito do ponto de vista da IA. Como a IA está avaliando uma conversa da qual participou, pode haver viés de autoavaliação. Os resultados numéricos citados são os que o usuário informou depois de rodar o código com os dados reais.

## 1. Como fui direcionada

**Começou pelo domínio, não pela solução.** A primeira mensagem trouxe o PDF do case, o contexto ("programo em Python e uso Git, mas não tenho experiência com finanças") e uma restrição explícita: "Antes de pensar em solução, quero entender o tema. [...] Não proponha solução nem código ainda". O pedido foi dividido em três perguntas: o que é cada indicador (cálculo, unidade e frequência), como um assessor os usa com clientes e quais cuidados existem ao compará-los.

**Conferia na fonte antes de seguir.** Depois da explicação inicial, o usuário foi ao SGS do Banco Central, conferiu os códigos, as unidades e a data do último valor de cada série e voltou com perguntas específicas. Por exemplo: por que a série 12 do CDI está em % ao dia, se eu tinha falado em % ao ano, e qual série usar para o acumulado. O mesmo padrão se repetiu em todas as etapas. Ele conferiu:
- a contagem de dias úteis da extração do CDI (1.526);
- o primeiro e o último valor da PTAX no site do BC;
- valores mensais do IPCA no SGS e em notícias do IBGE;
- os IPCA de dezembro no IBGE;
- os fechamentos de fim de ano do Ibovespa na B3;
- o fechamento do Ibovespa de 26/10/2026 em notícia.

**Deu restrições claras de trabalho:**
- preferência explícita por "algo simples e funcional do que um complexo e inacabado";
- prazo próprio ("minha meta é entregar até quarta");
- ambiente informado de saída (Windows, PowerShell, Python 3.11.9, pandas 3.1.0), com a instrução "o pandas é a versão 3.x [...] considere isso em todo o código";
- repositório `pipeline-mercado`, com uma branch por etapa e commits incrementais.

**Pediu plano antes de código, de forma consistente.** Antes da primeira linha de código, pediu críticas às perguntas do dashboard, um plano em etapas, a estrutura de pastas e as ferramentas, com a instrução: "explique todas as decisões tomadas por você e me fale o ônus e o bônus de cada uma para eu tomar a decisão se coloco ou não". Esse ciclo se repetiu em praticamente todo passo: "antes do código, me explique [...] com o ônus e o bônus de cada opção" → eu apresentava as opções → ele escolhia (às vezes com ajustes) → eu escrevia o código. Também pediu explicação linha a linha do `config.py`.

**Um passo de cada vez, com retorno de resultados.** O trabalho seguiu as Etapas 0 a 6 em passos pequenos ("um passo de cada vez, igual na etapa 1"). A cada passo, o usuário rodava o código, conferia os números e os reportava antes de pedir o próximo.

**Nível de detalhe.** As instruções eram em geral detalhadas e vinham com justificativa. Com frequência, ele trazia a própria análise junto: por que escolheu a convenção D-1, por que um aviso para períodos com menos de 2 dias, por que o fechamento do Yahoo em 29/12/2022 estava errado. Algumas instruções foram curtas ou ambíguas e exigiram interpretação minha: "eu ainda to dentro do limite?", "sem decimais e variação do dia", "troque as cores das duas" e o rótulo "Notas valores brutos de impostos". Em todos esses casos, eu disse qual interpretação adotei.

**Trouxe opinião de terceiros para avaliação.** Na Etapa 5, apresentou a sugestão de um contato da área financeira (trocar as duas linhas do bloco E por um gráfico só de juro real) e pediu ônus e bônus antes de decidir.

**Pediu textos prontos para a documentação**, como frases para as seções de limitações e decisões do README.

## 2. Pedidos principais

1. **Entender o tema antes de projetar (28/10).** Explicar CDI, IPCA, PTAX e Ibovespa (definição, cálculo, unidade e frequência), o uso de cada um por um assessor e os cuidados ao comparar séries de frequências e naturezas diferentes, sem propor solução nem código.
2. **Criticar as perguntas do dashboard e montar um plano.** Dizer quais perguntas usar, quais tirar e quais acrescentar, e montar um plano em etapas, com estrutura de pastas e ferramentas, explicando cada decisão técnica com ônus e bônus e deixando a atualização incremental como etapa opcional. Em seguida, o próprio usuário enxugou o escopo para caber no prazo.
3. **Implementar etapa por etapa, explicando antes de codificar.** Um passo por vez, com a explicação das decisões antes do código: a convenção de data do CDI, o tratamento do fim de séries com atrasos de publicação diferentes, o mês do IPCA, o fuso horário do yfinance e as colunas em dois níveis do `yf.download`. Tudo considerando o pandas 3.x.
4. **Validar contra fontes oficiais, com tolerância justificada e erros claros.** CDI × série 4391 do SGS, IPCA em 12 meses × IBGE e Ibovespa × B3, incluindo como tratar um fechamento comprovadamente errado do Yahoo (29/12/2022) sem tornar a validação circular.
5. **Desenhar e refinar o dashboard.** Cartões com a data de cada dado, comparativo em base 100 com seletor de data, juro real em 12 meses (Etapas 5 e 6) e, por fim, um layout de painel com os dois gráficos lado a lado, as notas recolhidas e a altura ajustada para notebook.

## 3. Correções e questionamentos

| # | Momento | O que eu fiz ou sugeri | O que o usuário apontou ou decidiu |
|---|---|---|---|
| 1 | Escopo inicial | Propus cinco blocos (A–E), incluindo o D (IPCA com a faixa da meta), e validações também contra a série 4389 e conferências da PTAX e do Ibovespa. | Cortou o D, por exigir dados manuais, e limitou as validações iniciais a CDI × 4391 e IPCA × IBGE. O bloco B ficou opcional. |
| 2 | Etapa 1 | Escrevi que "a extração está no `extract.py`" e expliquei o código, mas não criei o arquivo. | Apontou que o arquivo não tinha vindo. Entreguei na resposta seguinte. |
| 3 | Etapa 1 | Ao estimar o índice final do CDI, escrevi "somando os anos completos de CDI acumulado". | Perguntou se o certo não seria multiplicar. Estava certo: juros compostos se multiplicam (o código já multiplicava). **Não respondi esse ponto explicitamente** na resposta seguinte. |
| 4 | Etapa 1 | Estimei o índice em 01/10/2021 em cerca de 1,05. | Mostrou que o arquivo tinha 1,0301, e que por isso a linha terminava perto de 183, e não de 180. Reconheci o erro: o CDI estava entre 2% e 5% ao ano naquele período. |
| 5 | Etapa 1 | Primeira versão do gráfico. | Encontrou o bug: escolhendo a última data, o gráfico ficava com um ponto só e vazio. **Propôs a regra** de mostrar um aviso quando houver menos de 2 dias com dado, com argumentos: não esconde datas válidas, não depende de um número arbitrário e segue a lógica do pipeline de avisar em vez de esconder. Implementei a regra dele. |
| 6 | Etapa 1 | Recomendei o `tickformatstops` com rótulo de dia `%d/%m`. | Aceitou a opção, mas trocou o rótulo para `%d/%m/%y`, para não ficar ambíguo na virada do ano. |
| 7 | Etapa 1 | Com a maior diferença da validação em 0,0050 (exatamente a tolerância), sugeri investigar o mês e levantei a hipótese de a 4391 usar uma janela deslocada. | Mostrou que fev/2022 dava 0,75504 contra 0,76, a 0,00004 da borda do arredondamento, e que com a janela deslocada out/2021 e dez/2021 teriam reprovado. Com isso, confirmou com dados a convenção D-1. |
| 8 | Etapa 2 | — | Identificou que a linha a mais da PTAX era atraso de publicação do CDI (rodou num sábado) e não diferença de calendário, e perguntou como tratar o 30/10. |
| 9 | Etapa 3 | Gravação da tabela mensal. | Encontrou o bug (a coluna `mes` saía como `2020-10-31`), diagnosticou a causa (o `date_format` do `to_csv` também formata colunas de período) e pediu a correção sem alterar o `diario.csv`. |
| 10 | Etapa 3 | Validação do IPCA. | Acrescentou dois requisitos: parar com mensagem clara se um mês de referência não existir, e mostrar a tolerância do mês da maior diferença. |
| 11 | Etapa 3 | Paleta de cores. | Apontou que o IPCA (laranja) e o Ibovespa (vermelho-alaranjado) ficariam parecidos lado a lado. Interpretei como "deixar bem diferentes" e mudei o IPCA para roxo-avermelhado. |
| 12 | Etapa 4 | Previ que o Ibovespa faltaria só em 24 e 31/12. | Corrigiu: até 2021, a B3 fechava nos feriados de São Paulo (20/11/2020, 25/01/2021, 09/07/2021), e o último pregão do ano variou (29/12/2022, 28/12/2023). Decidiu não prever a lista e deixar o relatório mostrar as faltas reais. Depois, explicou cada uma das 13. |
| 13 | Etapa 4 | Sugeri como referência fechamentos encontrados em notícias. | Escolheu o último pregão de cada ano, para cobrir o período inteiro, conferido na própria B3. |
| 14 | Etapa 4 | — | Detectou que o Yahoo tinha 110.031 em 29/12/2022, contra 109.734,60 na B3, e demonstrou com a variação do dia e a abertura seguinte. Eu apontei uma inconsistência nos valores dele (109.734,60 numa mensagem e 109.735,00 em outra), e ele confirmou 109.734,60. |
| 15 | Etapa 4 | Sugeri usar a comparação "fechamento × abertura seguinte" como detector de fechamentos errados. | Aceitou só como relatório informativo, sem parar o pipeline. Com os dados reais (1.513 pares, 440 iguais, 763 com diferença acima de 1 ponto), mandou remover, porque a hipótese não se sustentou, e pediu uma frase para as limitações. |
| 16 | Etapa 4 | Textos do dashboard. | Acrescentou conteúdo que eu não tinha proposto: a PTAX como taxa de referência, e não a cotação de compra; o IR pela tabela regressiva (22,5% a 15%), exceto LCI e LCA; a meta de inflação no cartão do IPCA, como constante com a fonte (CMN). |
| 17 | Etapa 5 | — | Percebeu que `pontos_ipca` criaria um ponto vazio no mês só com CDI e diria "até out/2026", e pediu para conferir o resto do app e da validação. Eu não tinha previsto isso. Ao conferir, achei mais um ponto afetado (a mensagem de erro da validação do IPCA). |
| 18 | Etapa 5 | — | Trouxe a sugestão do contato da área financeira para o bloco E e pediu avaliação antes de adotar. |
| 19 | Etapa 6 | Estimei que, para caber tudo em 768 px sem rolar, os gráficos ficariam com 250 a 300 px. Propus cortes de altura e 300 px. | Redefiniu o objetivo, que inicialmente era dele: caber tudo sem rolar deixaria os gráficos pequenos demais, então basta os dois aparecerem inteiros lado a lado, com as notas abaixo. Fixou a altura inicial em 350 px e não aceitou o corte por CSS. |

## 4. Divisão das decisões

Em resumo: a maior parte das escolhas de **implementação** (bibliotecas, formatos, funções, tolerâncias, tratamento de casos de borda) foi proposta por mim e aprovada pelo usuário. As decisões de **escopo**, de **o que mostrar ao cliente**, as **referências oficiais** usadas na validação e as **correções de erros** vieram do usuário.

### Decididas pelo usuário

Por iniciativa dele, ou escolhendo entre opções que apresentei com justificativa própria:

- Ordem do trabalho: entender o domínio, depois planejar e só então codificar, um passo por vez, com uma branch por etapa e conferência com dados reais a cada passo.
- Escopo: blocos A, C e E; B opcional, depois registrado como melhoria futura; D cortado; validações iniciais limitadas a CDI × 4391 e IPCA × IBGE.
- Nome do repositório e restrições de ambiente (Windows/PowerShell, pandas 3.x).
- Convenção D-1 do CDI, escolhida entre as opções que apresentei, com justificativa própria: o CDI e o Ibovespa medem o mesmo período no base 100.
- Aviso quando o período tem menos de 2 dias com dado (proposta dele).
- Rótulo de dia `%d/%m/%y` no eixo.
- Opção 4 para o fim das séries (nada inventado, cada série até o próprio último dado), justificada pelo mesmo critério da D-1.
- Cores distintas por série e a troca da cor do IPCA.
- Valores de referência do IPCA (IBGE) e do Ibovespa (B3), conferidos por ele, e a escolha do último pregão de cada ano.
- Na validação do IPCA: parar com mensagem clara se faltar mês de referência e mostrar a tolerância do pior mês.
- Deixar o relatório de calendário mostrar as faltas reais, em vez de prever uma lista.
- Corrigir 29/12/2022 por um registro de correção (escolhido entre as opções que apresentei).
- Manter o relatório de fechamento × abertura só como informativo e, depois, removê-lo.
- Textos sobre a PTAX e o IR, e a meta no cartão do IPCA.
- Reaproveitar `variacao_mensal_d1` e `variacao_acumulada` para o CDI mensal e em 12 meses, e calcular o juro real pela divisão (ideia dele, que pediu a confirmação com exemplo).
- Adotar o gráfico só de juro real (sugestão do contato financeiro, avaliada antes).
- Validar o juro real com um mês conferido à mão, sem checagem automática.
- Layout de painel: cartões em cima; colunas de 60% e 40%; seletor dentro da coluna da esquerda; notas em expander; rótulo "Ibovespa (pontos)"; altura de 350 px; objetivo de rolagem mínima, e não zero.

### Sugeridas por mim e aceitas sem alteração

- Série 12 como base do CDI, anualizada para o cartão, com validação contra a 4391.
- Reformular as perguntas do dashboard como "réguas" de referência para o assessor, com a estrutura em blocos.
- Ferramentas e arquitetura:
  - Streamlit + Plotly, com `app.py` na raiz;
  - `requests` direto na API do SGS;
  - yfinance via `Ticker.history`, com `Close` e `auto_adjust=False`;
  - CSV em `data/raw` e `data/processed`;
  - venv e `requirements.txt` com versões fixas, incluindo o `curl_cffi` fixado com comentário;
  - estrutura de pastas e ordem das etapas.
- Período: análise a partir de 01/10/2021, folga de 12 meses derivada no config e dados até ontem.
- `config.py` só com valores, com os caminhos calculados a partir do próprio arquivo.
- Tolerância de 0,005 p.p. para o CDI, em vez de arredondar e exigir igualdade.
- "Só meses fechados" por construção, usando o primeiro dia útil do mês seguinte.
- Validar antes de gravar e parar se alguma validação reprovar.
- União das datas, com preenchimento só entre datas reais (`ffill(limit_area="inside")`) e um relatório de calendários.
- O mês do IPCA como período (`Period`), gravado como `AAAA-MM`.
- Tolerância do IPCA calculada pelo pior caso do arredondamento, com as referências como constante no `validate.py`, incluindo set/2026.
- IPCA no base 100: pontos próprios, base no mês anterior ao início, linha reta com marcadores, mês no texto do mouse e nomes de meses em português por uma lista fixa.
- Ibovespa:
  - raw com o fuso original;
  - fuso removido sem conversão, com a exigência de hora 00:00;
  - tolerância de 1 ponto;
  - validação feita sobre o dado antes da correção, com aviso de correção obsoleta;
  - aviso do pandas deixado visível e documentado no README.
- Cartão do Ibovespa sem decimais, quatro cartões numa linha agrupados por tipo, legenda em lista e a redação "intervalo de 1,5% a 4,5%" para a meta.
- Validação feita sobre a coluna gravada `cdi_mes`, e CDI e IPCA em 12 meses na caixa do mouse do juro real.
- Etapa 6 (o usuário aceitou todas as recomendações):
  - juro real sempre com o período completo, em cinza médio, com faixa suave abaixo do zero;
  - títulos de seção e linha de fontes no topo;
  - intervalo do eixo definido à mão, com `cliponaxis=False`;
  - salto de 26/10/2026 registrado só no README;
  - rentabilidade em 1, 3 e 5 anos como melhoria futura;
  - texto da legenda do juro real.
- No layout: os cortes de altura de (a) a (e), as explicações no "?" dos cartões e a principal ressalva no rótulo das notas.

### Sugeridas por mim e aceitas com ajuste

- Formato do eixo de datas: a opção que recomendei, com o rótulo de dia trocado para `%d/%m/%y`.
- Paleta Okabe-Ito, com a troca da cor do IPCA.
- Detector de fechamento × abertura: aceito só como informativo e depois removido.
- Altura dos gráficos: 350 px em vez dos 300 que propus, com o objetivo de rolagem redefinido.

## 5. Pontos de atenção

### Como o código foi testado por mim

- **Não tive acesso ao repositório nem à máquina do usuário.** Trabalhei só com os arquivos que eu mesmo gerei e com os resultados que ele reportou. Edições manuais que ele fez não foram revisadas por mim.
- **Etapas 1 a 3:** o código foi entregue sem nenhuma execução minha. A verificação foi a do usuário, com os dados reais.
- **Etapas 4 a 6:** testei num ambiente separado e offline, com Python 3.13 e pandas 3.0.5. O projeto usa Python 3.11.9 e pandas 3.1.0. O yfinance, o Streamlit e o Plotly não puderam ser instalados, então usei versões falsas que só registram o que seria exibido, sobre dados sintéticos no formato das fontes.
- **Nunca vi a aparência do dashboard.** A última versão, com o layout de painel, ainda não tinha sido executada pelo usuário quando este relatório foi gerado. Precisam ser conferidos na tela: o alinhamento do título com a caixa de data, a legenda do Plotly com margens de 10 px, o texto "empate com a inflação" perto da borda superior e o "?" dos cartões.
- **A meta no `app.py` foi reescrita por mim** sem ver a versão que o usuário já tinha alterado (com o intervalo como constante). Os nomes e o texto podem divergir do que ele fez.
- **As versões do yfinance e do curl_cffi no `requirements.txt` não foram conferidas por mim.** O usuário ia informá-las, e esse retorno não aconteceu na conversa.

### Fatos que vieram de pesquisa ou do meu conhecimento

- **Regras de IR** (tabela regressiva de 22,5% a 15%; isenção de LCI e LCA para pessoa física em 2026): conferidas em blogs e portais de investimento de agosto e setembro de 2026, não na legislação. Convém verificar na data da entrega.
- **Meta de inflação** (3%, intervalo de 1,5% a 4,5%, Resolução CMN nº 5.141/2024, mudanças com 36 meses de antecedência): tirada de uma carta do BC e de notícias. Convém conferir na página do BC.
- **Metodologias da taxa DI, da PTAX e do Ibovespa (retorno total) e o calendário da B3:** vieram de páginas da B3 e do BC e de portais. No calendário, eu errei em parte (item 12 da seção 3).
- **A causa do espaço vazio no eixo** (o Plotly acrescenta 5% de margem quando alguma série tem marcadores): veio do meu conhecimento do código do Plotly. É compatível com o que o usuário viu, mas não conferi na documentação.
- **A tolerância do IPCA** se apoia numa suposição minha, a de que o IBGE calcula o acumulado a partir do número-índice e só depois arredonda. A fórmula é uma aproximação de primeira ordem do pior caso.
- **A explicação de por que a PTAX subiu mais que o dólar comercial em 26/10/2026** (as duas medem horários diferentes do dia) é plausível, mas não foi verificada com dados intradiários.

### Escolhas com margem pequena ou cobertura parcial

- **CDI × 4391:** a maior diferença ficou em 0,0050 p.p., exatamente na tolerância (fev/2022, a 0,00004 da borda). Se o BC arredondar de outra forma, um mês pode reprovar sem que haja erro.
- **Ibovespa:** só 5 dias foram conferidos contra a B3. O erro de 29/12/2022 mostra que outros dias também podem estar errados, e o detector automático que propus não funcionou e foi removido. A correção de 29/12/2022 é um valor digitado à mão.
- **PTAX:** sem validação automática; só o primeiro e o último valor foram conferidos à mão.
- **CDI ao ano no cartão:** a anualização não tem validação automática, porque a série 4389 ficou de fora por decisão de escopo.
- **Juro real:** validado só de forma indireta (os componentes são validados) e por um mês conferido à mão.
- **Dependência de rede:** o pipeline baixa todas as séries a cada execução e também precisa de internet para validar, porque a 4391 é baixada na hora. Sem rede, nada é gravado.
- **"Dados até ontem"** usa a data do computador em que o pipeline roda.

### Erros e interpretações meus que convém conferir

- Os erros já listados na seção 3: o `extract.py` prometido e não entregue; "somando" em vez de multiplicando, sem que eu reconhecesse explicitamente; a estimativa de 1,05; a lista incompleta de dias sem pregão; e o detector de fechamento × abertura, que os dados não sustentaram.
- Interpretações de instruções ambíguas:
  - "sem decimais e variação do dia": entendi como sem as duas coisas, ou seja, sem decimais e sem a variação do dia;
  - "troque as cores das duas": entendi como deixar o IPCA e o Ibovespa bem diferentes;
  - "Notas valores brutos de impostos": usei "Notas (valores brutos de impostos)", com parênteses.
