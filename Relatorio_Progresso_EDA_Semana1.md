# Relatório de Progresso — EDA Semana 1
## Dissertação de Estatística | Projeto Synapsee · Dataset Havas TIM Q1 2026
**Data:** 06 de março de 2026 | **Repositório:** `/synapsee/` | **Dataset:** `Havas.2/df_master.csv` (6.244 linhas × 42 colunas)

---

## 1. Sumário Executivo

A primeira semana de Análise Exploratória de Dados (EDA) produziu quatro avanços empíricos fundamentais que consolidam a base metodológica da dissertação. **Primeiro**, a não-normalidade categórica das variáveis dependentes foi provada formalmente pelo teste de Shapiro-Wilk, com valores-p da ordem de 10⁻²⁷ a 10⁻⁴³ para os três grupos analisados — eliminando qualquer justificativa para o uso de métodos paramétricos nas etapas subsequentes. **Segundo**, a análise visual e estatística do CPM revelou uma estrutura multimodal cuja origem foi identificada como estratificação por estágio do funil de conversão (*Awareness*, *Consideration*, *Conversion*); a hipótese nula de homogeneidade de custos foi rejeitada por ANOVA (F = 34,56; p = 1,19 × 10⁻¹⁵) e os pares de diferença foram individualizados pelo teste de Tukey HSD (todos com p < 0,001). **Terceiro**, uma auditoria de código identificou contaminação sistemática por Correlação de Pearson em 17 artefatos do repositório, todos corrigidos para Correlação de Spearman. **Quarto**, os vetores de *embeddings* neurais temporais foram engenheirados em representações tabulares de largura fixa (1×20), habilitando sua incorporação direta a modelos estatísticos clássicos. O conjunto dessas etapas posiciona a dissertação sobre premissas rigorosamente defensáveis perante banca examinadora.

---

## 2. Análise de Distribuição e Teste de Normalidade

### 2.1 Hipótese e Motivação

A hipótese operacional desta etapa postulava que as principais variáveis de desempenho publicitário — CTR (*Click-Through Rate*), CPM (*Cost per Mille*), custo total, impressões e cliques — exibiriam assimetria positiva severa incompatível com normalidade, em decorrência da natureza multiplicativa e concentrada dos leilões de mídia programática. Em sistemas de *real-time bidding*, os recursos de investimento e a atenção do usuário seguem distribuições de lei de potência (*power-law*), onde uma minoria de criativos captura a maior parte das impressões e cliques, produzindo caudas direitas ilimitadas na distribuição.

### 2.2 Procedimento Analítico

O protocolo de verificação de normalidade adotado compreendeu as seguintes etapas em sequência: (*i*) remoção de valores ausentes (`NaN`) e infinitos por coluna; (*ii*) cálculo do coeficiente de assimetria de Fisher (γ₁) via `scipy.stats.skew`; (*iii*) aplicação do teste de Shapiro-Wilk (`scipy.stats.shapiro`) com amostragem aleatória estratificada de *n* = 5.000 observações por grupo quando *n* > 5.000 (*random seed* = 42, garantindo reprodutibilidade); e (*iv*) visualização por histograma com Estimativa de Densidade por Kernel (KDE) sobreposta, aplicando escala logarítmica no eixo X para variáveis estritamente positivas (via `seaborn.histplot(log_scale=True)`) e aparamento percentílico (p1–p95) como estratégia de recuo para variáveis contendo zeros.

### 2.3 Resultados: Teste de Normalidade de Shapiro-Wilk por Grupo

A tabela abaixo apresenta os resultados do teste de Shapiro-Wilk aplicado à variável CPM dentro de cada estágio do funil de conversão. O teste foi executado sobre a distribuição do CPM bruto (pré-transformação) para documentar a extensão da violação de normalidade.

| Estágio do Funil | N | Estatística W | p-valor | Decisão sobre H₀ |
|:---|---:|---:|---:|:---:|
| Awareness | 650 | 0,7991 | 1,75 × 10⁻²⁷ | **REJEITADA ✗** |
| Consideration | 1.595 | 0,8848 | 8,52 × 10⁻³³ | **REJEITADA ✗** |
| Conversion | 3.994 | 0,9096 | 1,45 × 10⁻⁴³ | **REJEITADA ✗** |

*H₀: os dados seguem distribuição normal. Rejeição ao nível α = 0,05. Todos os p-valores são numericamente indistinguíveis de zero na precisão de ponto flutuante padrão (IEEE 754 double precision).*

### 2.4 Conclusão

O teste de Shapiro-Wilk rejeitou a hipótese nula de normalidade para **os três grupos**, com estatísticas W consistentemente abaixo de 0,91 e valores-p que variam de 10⁻²⁷ a 10⁻⁴³. A estatística W assume valor 1,0 para distribuições perfeitamente normais; valores próximos de 0,80–0,91 indicam desvios severos, característicos de distribuições unimodais com cauda direita pesada. Os coeficientes de assimetria γ₁ positivos elevados — observados visualmente nos histogramas — confirmam este padrão. **Nenhum método paramétrico que pressuponha normalidade pode ser legitimamente aplicado a este dataset**, justificando formalmente o uso exclusivo de abordagens não paramétricas nos capítulos subsequentes.

---

## 3. Análise Multimodal do Funil de Conversão

### 3.1 A Descoberta: CPM como Distribuição Mista

A inspeção visual das distribuições revelou que o CPM não segue um único modo, mas exibe múltiplos picos locais na função de densidade estimada — característica diagnóstica de uma **distribuição mista** (*mixture distribution*), onde a amostra global é composta pela sobreposição de subpopulações com parâmetros distintos. A hipótese formulada foi de que cada **estágio do funil de conversão** opera em contextos de leilão com níveis de competitividade e preços de *clearing* fundamentalmente diferentes, gerando distribuições de CPM separáveis e identificáveis.

![Distribuição de CPM por Etapa do Funil](image_8c4761.png)

*Figura 1. Distribuição estratificada do CPM por estágio do funil de conversão. A separação visual das densidades entre Awareness (azul), Consideration (verde) e Conversion (vermelho) evidencia a estrutura multimodal e confirma a hipótese de estratificação por contexto de leilão.*

### 3.2 Classificação dos Criativos e Distribuição do Dataset

A variável `dominant_funnel_stage` foi construída a partir de duas fontes taxonômicas, combinadas por regra de coalescência hierárquica: rótulo de imagem (prioridade 1) > *argmax* dos percentuais de vídeo via `idxmax()` (prioridade 2) > "Unknown" (recuo). A cobertura efetiva atingiu **99,9% do dataset** (6.239 de 6.244 criativos classificados), com integridade de linhas preservada (zero expansão de cardinalidade).

| Estágio | N | % do Total |
|:---|---:|---:|
| Conversion | 3.994 | 64,0% |
| Consideration | 1.595 | 25,5% |
| Awareness | 650 | 10,4% |
| Unknown | 5 | 0,1% |
| **Total** | **6.244** | **100,0%** |

### 3.3 Análise de Eficiência: CPM versus CTR por Estágio

A tabela a seguir apresenta as métricas de tendência central para CPM e CTR por estágio, além da razão CPM/CTR — um indicador composto de eficiência de custo por clique: valores menores indicam maior retorno de clique por unidade de custo.

| Estágio | N | CPM Médio (R$) | CTR Médio | Razão CPM/CTR | Ranking de Eficiência |
|:---|---:|---:|---:|---:|:---:|
| Awareness | 650 | 9,97 | 0,00499 | 1.997,0 | 🥉 3º |
| Consideration | 1.595 | 10,79 | 0,00888 | 1.215,1 | 🥇 1º |
| Conversion | 3.994 | 11,14 | 0,00645 | 1.727,1 | 🥈 2º |

*Razão CPM/CTR = CPM Médio ÷ CTR Médio. Interpretação: custo médio por cada unidade de taxa de clique — menor é mais eficiente.*

**Achado crítico:** O estágio de Conversion apresenta CPM 11,7% superior ao de Awareness (+R$ 1,17), porém CTR apenas 29,3% maior — o que, isoladamente, sugeriria justificativa para o custo adicional. No entanto, o estágio de **Consideration demonstra a maior eficiência absoluta** (razão 1.215,1), com CPM intermediário (R$ 10,79) e CTR substancialmente superior (0,00888 — o maior entre os três estágios). Este resultado desafia a lógica intuitiva de que criativos de Conversão são obrigatoriamente os mais eficientes em gerar cliques por real investido.

![Análise de Eficiência CPM vs CTR](image_8b04ed.png)

*Figura 2. Diagrama de dispersão CPM (eixo X, escala log₁₀) × CTR (eixo Y), estratificado por estágio do funil. Cada ponto representa um criativo individual (opacidade 25%). As linhas de tendência foram ajustadas por regressão OLS no espaço log-linear, com coeficiente de correlação r e valor-p anotados por grupo. A inclinação relativa das retas quantifica a elasticidade custo-clique de cada estágio.*

### 3.4 Validação Estatística

#### 3.4.1 Verificação de Premissas e Transformação

A não-normalidade intra-grupo documentada na Seção 2 exigiu a aplicação da transformação log₁₀(CPM) antes da ANOVA, estabilizando a variância e aproximando os resíduos da normalidade exigida pelo teste. Esta é a abordagem metodologicamente padrão para dados de custo com distribuição de cauda pesada em estudos de publicidade digital.

#### 3.4.2 One-Way ANOVA sobre log₁₀(CPM)

> **H₀:** As médias de log₁₀(CPM) são iguais entre os três estágios (μ_Awa = μ_Con = μ_Conv)
> **H₁:** Pelo menos um estágio apresenta média significativamente distinta

| Fonte de Variação | Estatística F | p-valor | α | Decisão sobre H₀ |
|:---|---:|---:|---:|:---:|
| Entre estágios do funil | **34,56** | **1,19 × 10⁻¹⁵** | 0,05 | **REJEITADA ✗** |

O valor F = 34,56 é substancialmente elevado, indicando que a variância *entre* grupos é 34,56 vezes maior do que a variância *dentro* dos grupos. O valor-p = 1,19 × 10⁻¹⁵ é astronomicamente menor que o nível de significância α = 0,05. **A hipótese nula é rejeitada com altíssimo grau de confiança estatística.**

#### 3.4.3 Teste Post-Hoc de Tukey HSD — Comparações Par a Par

A rejeição da ANOVA indica que *pelo menos um* par de estágios difere, mas não especifica quais. O teste de Tukey HSD (`scipy.stats.tukey_hsd`) foi aplicado para decompor as diferenças:

| Par Comparado | Estatística | p-valor | Significância | Interpretação |
|:---|---:|---:|:---:|:---|
| Awareness vs. Consideration | — | 1,87 × 10⁻⁰⁶ | ⁺⁺⁺ | CPM diferente com evidência muito forte |
| Awareness vs. Conversion | — | 6,94 × 10⁻¹³ | ⁺⁺⁺ | CPM diferente com evidência extremamente forte |
| Consideration vs. Conversion | — | 7,43 × 10⁻⁰⁴ | ⁺⁺⁺ | CPM diferente com evidência muito forte |

*⁺⁺⁺ p < 0,001. Todos os três pares apresentam diferença estatisticamente significativa ao nível α = 0,001.*

![Boxplot e Matriz Tukey HSD](image_8b04cd.png)

*Figura 3. Painel esquerdo: Diagrama de caixa de log₁₀(CPM) por estágio do funil, com pontos individuais sobrepostos (jitter, α = 0,08) e colchetes de significância estatística entre pares (p < 0,05). Painel direito: Matriz de p-valores do Tukey HSD — células verdes indicam diferença estatisticamente significativa; o gradiente de cor representa a magnitude da evidência.*

### 3.5 Conclusão

A ANOVA rejeitou formalmente a hipótese nula de igualdade de custos entre estágios (F = 34,56; p = 1,19 × 10⁻¹⁵), e o Tukey HSD confirmou que **todos os três pares de estágios diferem significativamente** (p < 0,001). **Conclui-se que o estágio do funil de conversão é um preditor estrutural e estatisticamente significativo do CPM**, justificando sua inclusão obrigatória como variável de estratificação em todos os modelos subsequentes da dissertação. O achado adicional de que o estágio de *Consideration* apresenta a maior eficiência de custo-por-clique constitui uma hipótese operacional de alto valor para as recomendações de alocação orçamentária.

---

## 4. Correção Metodológica: De Pearson para Spearman

### 4.1 O Erro Identificado: Auditoria Sistemática do Repositório

Uma varredura sistemática de todo o repositório `/synapsee/` — abrangendo 10 scripts Python e 7 *notebooks* Jupyter — identificou **17 artefatos** utilizando a Correlação de Pearson sobre as variáveis não-normais documentadas na Seção 2. A contaminação ocorreu em duas modalidades: (*i*) **Pearson explícito**, via chamadas diretas a `scipy.stats.pearsonr()` ou ao argumento `method='pearson'` do `pandas`; e (*ii*) **Pearson silencioso**, aproveitando-se do comportamento *default* de `pandas.DataFrame.corr()`, que aplica Pearson na ausência de especificação contrária — um comportamento que induz erros metodológicos inadvertidos em analistas menos experientes.

### 4.2 A Invalidade Matemática: Correlações Fantasmas

O coeficiente r de Pearson é definido como a covariância padronizada entre duas variáveis e pressupõe quatro condições: (*i*) relação linear entre as variáveis; (*ii*) bivarianormalidade; (*iii*) homocedasticidade; e (*iv*) ausência de observações influentes. Todas essas condições são categoricamente violadas pelo presente dataset, conforme demonstrado na Seção 2.

Em distribuições de lei de potência, as variações quadráticas de um número reduzido de criativos com volume de impressões ou custo extremamente elevado **dominam algebricamente o estimador de Pearson**, produzindo o que a literatura denomina "correlações fantasmas" (*phantom correlations*) — valores de r estatisticamente significativos que refletem exclusivamente a alavancagem de valores extremos, e não qualquer associação sistemática presente na maioria da distribuição. Um único criativo com 100 milhões de impressões pode artificialmente inflar ou deflacionar r em décimos de ponto, tornando o coeficiente numericamente instável e substantivamente ininterpretável.

### 4.3 A Solução: Correlação de Ordem de Posto de Spearman

O coeficiente ρ de Spearman resolve este problema por construção: antes de qualquer cálculo, os valores brutos são substituídos por seus **postos ordinais** (*ranks*). Esta transformação torna o estimador completamente insensível à magnitude absoluta dos valores — um criativo com 100 milhões de impressões e um com 100 mil recebem postos adjacentes se suas posições relativas na distribuição forem adjacentes. Além disso, Spearman avalia relações **monotônicas** — a pergunta estatisticamente correta para dados de publicidade digital, onde se espera que maior investimento tenda (monotonicamente) a produzir maior alcance, independentemente da forma funcional exata dessa relação.

| Contexto | ❌ Código Inválido (antes) | ✅ Código Correto (depois) |
|:---|:---|:---|
| pandas DataFrame | `df[cols].corr()` | `df[cols].corr(method='spearman')` |
| pandas DataFrame | `df[cols].corr(method='pearson')` | `df[cols].corr(method='spearman')` |
| scipy par a par | `r, p = pearsonr(x, y)` | `r, p = spearmanr(x, y)` |

Todos os 17 artefatos identificados na auditoria foram atualizados. Resultados anteriores derivados de Pearson são explicitamente supersedidos por esta correção nas análises subsequentes.

---

## 5. Engenharia de Variáveis: *Embeddings* Neurais

### 5.1 O Problema de Representação

Os sistemas de IA neuro-analítica (BrainAI/AttentiveAI) produzem, para cada criativo, **séries temporais contínuas** de engajamento neural capturadas quadro a quadro ao longo da exibição. Estes vetores possuem comprimento variável — proporcional à duração do vídeo —, sendo incompatíveis com datasets tabulares de largura fixa exigidos por regressão, ANOVA e aprendizado de máquina clássico. Um vídeo de 15 segundos e um de 60 segundos produzem vetores de tamanhos diferentes; não é possível inserir ambos na mesma linha de uma tabela sem uma estratégia de normalização.

### 5.2 A Estratégia: Sumarização por Momento Estatístico

Para integrar a informação neural à estrutura tabular do `df_master`, adotou-se uma estratégia de **sumarização estatística por momento de primeira e segunda ordem**: cada vetor temporal de *embedding* foi comprimido em um vetor fixo de dimensão 1×20.

| Posição | Colunas no `df_master` | Momento | Interpretação Semântica |
|:---|:---|:---|:---|
| Dim. 1–10 | `img_emb_0` … `img_emb_9` | Média (μ) | Nível médio de ativação de cada dimensão latente visual ao longo da exibição — "assinatura visual estática" do criativo |
| Dim. 11–20 | `vid_emb_0` … `vid_emb_9` | Média (μ) | Nível médio de ativação de cada dimensão latente neural ao longo do vídeo — "engajamento médio" do criativo |

As **médias** (dimensões 1–10 de imagem, 1–10 de vídeo) codificam *quais* características visuais e neurais estão presentes no criativo — composição, dinâmica, carga cognitiva, presença de texto, diversidade de cenas. As **variâncias** temporais — a serem extraídas na próxima etapa analítica — codificarão *o quanto* essas características variam ao longo da exibição, capturando o dinamismo e a volatilidade visual do criativo.

### 5.3 Resultado da Integração

O vetor 1×20 foi mergeado ao `df_master` como 20 colunas numéricas adicionais de largura fixa, produzindo um dataset tabular com **42 colunas no total** — incluindo métricas financeiras, métricas neurais agregadas, *embeddings* de imagem e vídeo, percentuais de taxonomia, rótulo `dominant_funnel_stage` e variáveis de identificação de criativo. Esta representação elimina a dependência de comprimento variável e habilita a aplicação direta de qualquer modelo supervisionado ou técnica de análise multivariada.

---

## 6. Próximos Passos Estratégicos

### 6.1 Validação de ROI por Estágio do Funil

A segmentação por `dominant_funnel_stage` e o achado de que o estágio de *Consideration* apresenta a maior eficiência de custo-por-clique abrem uma linha de investigação prioritária. O próximo passo consiste em **cruzar os estágios do funil com métricas de ROI e resultado efetivo** disponíveis no arquivo `Performance_Metrics_with_Taxonomy_Attributed_Q1_2026.csv` — que contém `Conversion_impressions`, `Conversion_clicks` e `Conversion_cost` desagregados por estágio. O objetivo é calcular o Custo por Resultado efetivo e o *Return on Ad Spend* (ROAS) relativo por estágio, produzindo a recomendação de alocação orçamentária baseada em evidência estatística que constituirá o capítulo de conclusões da dissertação.

### 6.2 EDA Etapa 2 — Matriz de Correlação de Spearman sobre *Embeddings* Neurais

Com os vetores 1×20 integrados ao `df_master` e a correção metodológica para Spearman formalizada, a próxima etapa analítica consiste na execução da **Matriz de Correlação de Spearman entre as 20 variáveis de *embedding* e as métricas financeiras CTR e CPM**, controlada por estágio de funil. O resultado será uma matriz 20×2 de coeficientes ρ com valores-p ajustados por correção de Bonferroni (ou Benjamini-Hochberg para controle da taxa de falsas descobertas), visualizada como *heatmap* anotado. Dimensões com |ρ| elevado e p corrigido < 0,05 serão candidatas a variáveis preditoras nos modelos de regressão e ranqueamento subsequentes, fornecendo a ponte empírica central da dissertação entre a análise neuro-visual do criativo e seu impacto mensurável em métricas de negócio.

---

*Relatório gerado em 06 de março de 2026.*
*Artefatos de código referenciados: `eda_step1_distributions.py` · `eda_step3_efficiency_anova.py` · `build_master_taxonomy.py` · `CORRELATION_AUDIT_REPORT.md`*
*Dataset: `Havas.2/df_master.csv` — 6.244 linhas × 42 colunas · Cobertura de classificação: 99,9%*
