import pandas as pd
import numpy as np
import os
import glob

# 1. Ajuste no carregamento e tratamento dos dados brutos
widths = [2, 8, 2, 12, 3, 12, 10, 3, 4, 13, 13, 13, 13, 13, 13, 13, 5, 18, 18, 13, 1, 8, 7, 13, 12, 3]
names = [
    "tipo_registro", "data_pregao", "cod_bdi", "cod_negociacao", "tipo_mercado", 
    "nome_empresa", "especificacao", "prazo_termo", "moeda", "preco_abertura",
    "preco_maximo", "preco_minimo", "preco_medio", "preco_ultimo", "preco_melhor_of_compra",
    "preco_melhor_of_venda", "numero_negocios", "quantidade_papeis", "volume_total",
    "preco_exercicio", "indicador_correcao", "data_vencimento", "fator_cotacao", 
    "preco_exercicio_pontos", "codigo_isin", "numero_distribuicao"
]

pasta_cotacoes = "Cotacao_Historica"
arquivos = sorted(glob.glob(os.path.join(pasta_cotacoes, "COTAHIST_A*.TXT")))

dfs = []
for arquivo in arquivos:
    print(f"Carregando {arquivo}...")
    df_temp = pd.read_fwf(arquivo, widths=widths, names=names, skipfooter=1, skiprows=1, encoding="latin1")
    
    # Filtragem precoce para evitar estouro de memória com múltiplos arquivos grandes
    cond_petr4 = (df_temp["cod_negociacao"].str.strip() == "PETR4") & (df_temp["tipo_mercado"] == 10)
    cond_opcoes = (df_temp["tipo_mercado"].isin([70, 80])) & (df_temp["nome_empresa"].astype(str).str.contains("PETR"))
    
    df_filtrado = df_temp[cond_petr4 | cond_opcoes]
    dfs.append(df_filtrado)

if not dfs:
    raise ValueError("Nenhum dado encontrado nos arquivos da pasta ou os arquivos estão vazios.")
df = pd.concat(dfs, ignore_index=True)

df["data_pregao"] = pd.to_datetime(df["data_pregao"], format="%Y%m%d")
df["data_vencimento"] = pd.to_datetime(df["data_vencimento"], format="%Y%m%d", errors='coerce')

# Ajustando o preço médio e o volume total com as casas decimais corretas
df["preco_abertura"] = df["preco_abertura"] / 100.0
df["preco_maximo"] = df["preco_maximo"] / 100.0
df["preco_minimo"] = df["preco_minimo"] / 100.0
df["preco_medio"] = df["preco_medio"] / 100.0
df["preco_ultimo"] = df["preco_ultimo"] / 100.0  # Mantido caso precise para a ação mãe
df["preco_exercicio"] = df["preco_exercicio"] / 100.0
df["volume_total"] = df["volume_total"] / 100.0

# Isolando a ação (PETR4) usando o preço de fechamento como referência do dia
df_petr4 = df[(df["cod_negociacao"].str.strip() == "PETR4") & (df["tipo_mercado"] == 10)]
df_preco_acao = df_petr4[["data_pregao", "preco_ultimo"]].rename(columns={"preco_ultimo": "preco_acao"})

# Filtrando as opções da Petrobras
df_opcoes = df[(df["tipo_mercado"].isin([70, 80])) & (df["nome_empresa"].str.contains("PETR"))].copy()
df_final = pd.merge(df_opcoes, df_preco_acao, on="data_pregao", how="inner")

# Janela de tempo de 30 dias antes do vencimento
df_final["dias_para_vencer"] = (df_final["data_vencimento"] - df_final["data_pregao"]).dt.days
df_final = df_final[(df_final["dias_para_vencer"] >= 0) & (df_final["dias_para_vencer"] <= 30)]

print("Salvando dados tratados em 'dados_tratados.csv'...")
df_final.to_csv("dados_tratados.csv", index=False)
print("Concluído!")
