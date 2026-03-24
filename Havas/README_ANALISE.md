# Como Executar a Análise Havas

Este guia explica como executar o notebook `havas_analisar.ipynb` que aplica os mesmos testes realizados nas bases GAIA e Tunad.

## Pré-requisitos

1. **Python 3.8+** instalado
2. **Jupyter Notebook** ou **JupyterLab** instalado
3. **Bibliotecas Python** necessárias:
   ```bash
   pip install pandas numpy matplotlib scipy scikit-learn
   ```
   
   Opcional (para análise XGBoost):
   ```bash
   pip install xgboost
   ```

## Como Executar

### Opção 1: Via Jupyter Notebook (Recomendado)

1. **Abra o terminal** e navegue até a pasta Havas:
   ```bash
   cd "/Users/tomasdefreitascarvalho/Desktop/Work Space/Rubens/synapsee/Havas"
   ```

2. **Inicie o Jupyter Notebook**:
   ```bash
   jupyter notebook
   ```
   
   Isso abrirá o Jupyter no seu navegador.

3. **Abra o arquivo** `havas_analisar.ipynb`

4. **Execute as células** em ordem:
   - Clique na primeira célula
   - Pressione `Shift + Enter` para executar
   - Continue executando célula por célula de cima para baixo
   - Ou use `Cell > Run All` para executar tudo de uma vez

### Opção 2: Via JupyterLab

1. **Inicie o JupyterLab**:
   ```bash
   jupyter lab
   ```

2. **Abra** `havas_analisar.ipynb` no JupyterLab

3. **Execute as células** como descrito acima

### Opção 3: Via VS Code / Cursor

1. **Instale a extensão Jupyter** (se ainda não tiver)

2. **Abra o arquivo** `havas_analisar.ipynb` no editor

3. **Clique em "Run All"** no topo do notebook, ou execute célula por célula

## Estrutura do Notebook

O notebook está organizado em seções:

1. **Carregar Dados**: Carrega índices de IA dos JSON e dados de performance do CSV
2. **Análise de Correlação**: Correlação de Pearson entre índices
3. **Análise de Quartis**: Comparação top 25% vs bottom 25%
4. **Regressão Linear**: Modelagem linear conjunta
5. **XGBoost**: Modelagem avançada (se disponível)
6. **Análise Temporal**: Primeiros 5 segundos para vídeos
7. **Análise por Segmento**: Análises segmentadas
8. **Resumo**: Resultados finais

## O que Esperar

- O notebook processará **todos os arquivos JSON** encontrados (pode ser mais que 426)
- Mostrará estatísticas sobre imagens vs vídeos
- Tentará fazer matching entre criativos e dados de performance
- Executará todas as análises estatísticas
- Gerará resultados comparáveis aos testes de GAIA e Tunad

## Troubleshooting

### Erro: "Module not found"
Instale as bibliotecas faltantes:
```bash
pip install <nome_da_biblioteca>
```

### Erro: "File not found"
Certifique-se de estar na pasta correta:
```bash
cd "/Users/tomasdefreitascarvalho/Desktop/Work Space/Rubens/synapsee/Havas"
```

### Erro: "XGBoost not available"
Isso é normal se o XGBoost não estiver instalado. O notebook continuará sem ele.

## Resultados

Os resultados serão exibidos diretamente no notebook. Você pode:
- Ver correlações entre índices
- Comparar grupos (quartis)
- Ver métricas de regressão (R², MSE)
- Analisar padrões temporais em vídeos
- Comparar segmentos diferentes
