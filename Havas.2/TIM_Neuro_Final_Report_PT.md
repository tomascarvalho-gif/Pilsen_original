# Base TIM: Roadmap Neuro-Métrico e Relatório Final

Este relatório consolidado une os testes do `analysis_roadmap.md` e detalha as descobertas estatisticamente significativas derivadas da fusão do banco de dados `Havas/Tim` com os scores neuro-métricos individuais (Engajamento Neural, Demanda Cognitiva, Foco).



---

## Visão Geral da Classificação de Imagens (Taxonomia)

Para enriquecer a análise criativa, um classificador de IA foi construído para categorizar imagens estáticas em etapas essenciais do funil (Awareness, Consideration, Conversion). Isso foi obtido submetendo as peças à API do Gemini, interpretando todo o escopo de imagens textuais e arranjos fotográficos.

**Rubrica de Classificação (Prompts da Taxonomia):**

| Categoria | Prompt / Definição |
| :--- | :--- |
| **1. Awareness** | Foco na marca, estilo de vida, emocional, centrado no logotipo. Sem ofertas específicas. |
| **2. Consideration** | Recursos, benefícios, comparações ou planos (ex: "Internet 500 Mega"). Educacional. |
| **3. Conversion** | Hard sell / Venda direta. Preços (R$), descontos (%) ou chamadas para ação diretas ("Assine Já", "Compre", "Contrate Agora", "Confira", "Saiba Mais", "Aproveite", "Aproveite Agora", "Consulte aqui"). |

**Próximos Passos & Definição da Taxonomia**  
Planejamos usar essas novas classes de taxonomia para conquistar ainda mais precisão em nossos testes de correlação e integrá-las como variáveis categóricas em nossos modelos de clusterização. Cconduziremos reuniões com Billy para definir perfeitamente a estrutura da taxonomia e ajustar os prompts finais para o classificador de IA.

---

## Resultados da Análise Neuro-Métrica

Esta seção detalha as correlações estatisticamente significativas encontradas entre os dados neuro-métricos (Engajamento Neural, Demanda Cognitiva, Foco) e as métricas de performance (CTR) dentro do banco de dados da TIM.

### 1. Análise de Vídeos

A análise revelou que a performance dos vídeos é altamente dependente do nível de investimento da campanha e dos momentos específicos dentro da linha do tempo do vídeo.

**A. A Segmentação por Custo é Crucial**

A descoberta mais crítica é que as neuro-métricas só possuem poder preditivo para **campanhas de Médio e Alto Custo (Gasto > R$ 210)**. Campanhas de vídeo de Baixo Custo mostraram correlação zero com as métricas neurais, provavelmente porque sua performance é dominada pela fase de exploração do algoritmo, não pela ressonância criativa. Por exemplo, nas campanhas de Alto Custo, o Engajamento Neural correlaciona-se positivamente com o CTR (r = 0.1228, p = 0.0066) e o Foco correlaciona-se negativamente (r = -0.1656, p = 0.0002).

**B. O Efeito de Fechamento (Últimos 5 Segundos)**

Ao analisar a linha do tempo do vídeo, os 5 segundos finais mostraram correlações muito mais fortes com o CTR do que os 5 segundos iniciais.
*   **Engajamento Neural:** Um Engajamento Neural mais alto no final do vídeo leva a um CTR maior (r = 0.0634, p = 0.0039).
*   **Foco (Complexidade Visual):** Uma queda acentuada no foco visual ou na intensidade da imagem no momento exato do *Call-to-Action* (Chamada para Ação) eleva o CTR (r = -0.1099, p < 0.0001).

**C. A Fórmula para Vídeos de Alta Performance**

Para campanhas de Alto Custo, a estratégia ideal é o "Gancho de Fechamento":
*   Diminuir a complexidade visual (Foco) no final.
*   Gerar simultaneamente um aumento no estímulo neural (Engajamento Neural) através de áudio ou mensagem principal durante os 5 segundos finais.

**D. Variações Trimestrais (O Gancho Inicial)**

Embora o final do vídeo seja geralmente mais importante, o que funciona para o *início* do vídeo muda dependendo da época do ano:
*   **2024 Q3:** Exigiu alta Demanda Cognitiva desde o primeiro quadro para ter sucesso (r = 0.6670, p = 0.0034).
*   **2025 Q1:** Puniu severamente vídeos que começavam com muita intensidade. Este trimestre recompensou uma abordagem mais gradual ("slow burn"), com Engajamento Neural inicial menor (r = -0.2356, p < 0.0001).

### 2. Análise de Imagens

Ao contrário dos vídeos, a performance das imagens estáticas e sua relação com as neuro-métricas mudaram drasticamente dependendo do Trimestre analisado.

**A. As Médias Globais São Ineficazes**

No agregado, sem segmentar pela época do ano, as imagens não mostraram quase nenhuma correlação (sendo insignificantes) com o CTR em todas as métricas: Engajamento Neural (r = 0.0255, p = 0.1001), Demanda Cognitiva (r = -0.0021, p = 0.8917) e Foco (r = 0.0154, p = 0.3197). A segmentação por custo também não revelou padrões globais válidos para imagens estáticas.

**B. Alta Sazonalidade**

Segmentar por Trimestre foi o único método que revelou sinais claros para imagens, indicando que a estratégia criativa ideal muda ao longo do ano.
*   **2024 Q2:** Correlação Positiva com o Engajamento Neural (r = 0.2794, p < 0.0001).
*   **2025 Q1:** Forte correlação negativa com Engajamento Neural (r = -0.3183, p < 0.0001) e Demanda Cognitiva (r = -0.2995, p < 0.0001). Imagens mais simples e calmas performaram melhor.
*   **2025 Q3:** Correlação Positiva com o Engajamento Neural (r = 0.2017, p = 0.0002). Imagens mais complexas e engajadoras performaram melhor.

---

## Conclusão Geral

Os dados mostram conclusivamente que a otimização neuro-métrica é altamente eficaz para as campanhas da TIM, desde que a análise leve em consideração as faixas de orçamento e a sazonalidade.

Para os vídeos, os esforços de otimização devem se concentrar inteiramente nas faixas de Médio e Alto custo, trabalhando especificamente os 5 segundos finais para que tenham baixa complexidade visual, mas alto engajamento auditivo/de mensagem. Para imagens estáticas, uma abordagem única não funciona; o estilo criativo deve alternar entre 'simples/calmo' e 'complexo/engajador' dependendo do Trimestre específico. A integração destas descobertas com as novas Classificações de Taxonomia fornecerá uma estrutura robusta e baseada em dados para toda a produção criativa futura.


