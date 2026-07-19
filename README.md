# Backtest de Opções - Petrobras (PETR4)

Este projeto foi configurado para rodar simulações de backtest com opções da Petrobras (PETR4) utilizando dados históricos da B3.

##  Requisitos e Instalação

Instalar as dependências no seu computador:
- **Pandas** e **NumPy**: Para manipulação e tratamento dos dados.
- **Matplotlib**: Para geração de gráficos.
- **Streamlit**: Para rodar o painel interativo (Dashboard).
- **OpenPyXL**: Para suporte a arquivos Excel.

As dependências estão listadas no arquivo requirements.txt.

---

##  Como Executar o Projeto

O projeto é dividido em etapas:

### Passo 1: Tratamento dos Dados Brutos
Os dados brutos das cotações históricas da B3 devem ser colocados na pasta Cotacao_Historica com a nomenclatura `COTAHIST_AYYYY.TXT` (ex: `COTAHIST_A2024.TXT`).

Você pode baixar os arquivos das séries históricas anuais diretamente no site da B3:
 **[Séries Históricas B3](https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/market-data/historico/mercado-a-vista/series-historicas/)**

Caso queira reprocessar os dados brutos da pasta `Cotacao_Historica`, execute:
```bash
python 01_tratamento_dados.py
```
*Isso lerá os arquivos `.TXT` de cotações históricas e gerará o arquivo `dados_tratados.csv`.*

### Passo 2: Executar o Motor do Backtest
Para rodar a simulação do backtest com os parâmetros padrão e gerar o arquivo de resultados (`resultados_backtest.csv`), execute:
```bash
python 02_backtest.py
```

### Passo 3: Visualizar os Resultados (Gráficos Estáticos)
Para visualizar o gráfico de evolução do PnL Acumulado e a distribuição de lucro/prejuízo por operação, execute:
```bash
python 03_plotar_resultados.py
```

---

##  Dashboard Interativo (Streamlit)

Para explorar os resultados de forma interativa, alterando parâmetros como margem de strike, alvo de lucro, tempo limite e capital investido, execute o dashboard:

```bash
python -m streamlit run app.py
```

>  **Nota:** Utilizamos o comando `python -m streamlit` para garantir que o Streamlit seja executado corretamente mesmo que a pasta de scripts do Python não esteja configurada no PATH do seu sistema.
