import pandas as pd
import numpy as np
import os
import glob
import matplotlib.pyplot as plt

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


# 2. Motor do Backtest Modificado
def rodar_backtest_atualizado(df):
    trades = []
    em_operacao = False
    
    dias_limite_saida = 5
    margem_strike = 0.05
    liquidez_minima = 1000000.0  # R$ 1 Milhão
    
    datas_pregao = df["data_pregao"].sort_values().unique()
    
    for data_atual in datas_pregao:
        dados_do_dia = df[df["data_pregao"] == data_atual]
        if dados_do_dia.empty:
            continue
            
        preco_acao_hoje = dados_do_dia["preco_acao"].iloc[0]
        
        if not em_operacao:
            # Lógica para identificar a entrada (5 dias após o vencimento anterior)
            condicao_entrada_valida = True 
            
            if condicao_entrada_valida:
                alvo_call = preco_acao_hoje * (1 + margem_strike) # OTM Call (acima do preço atual)
                alvo_put = preco_acao_hoje * (1 - margem_strike)  # OTM Put (abaixo do preço atual)
                
                # Aplicação do filtro de liquidez diária diretamente na seleção das opções
                calls_dia = dados_do_dia[(dados_do_dia["tipo_mercado"] == 70) & (dados_do_dia["volume_total"] >= liquidez_minima)]
                puts_dia = dados_do_dia[(dados_do_dia["tipo_mercado"] == 80) & (dados_do_dia["volume_total"] >= liquidez_minima)]
                
                if not calls_dia.empty and not puts_dia.empty:
                    # Encontra os strikes mais próximos dos alvos de 5%
                    call_escolhida = calls_dia.iloc[(calls_dia["preco_exercicio"] - alvo_call).abs().argmin()]
                    put_escolhida = puts_dia.iloc[(puts_dia["preco_exercicio"] - alvo_put).abs().argmin()]
                    
                    operacao_atual = {
                        "ticker_call": call_escolhida["cod_negociacao"],
                        "ticker_put": put_escolhida["cod_negociacao"],
                        "data_entrada": data_atual,
                        "preco_acao_entrada": preco_acao_hoje,
                        "strike_call": call_escolhida["preco_exercicio"],
                        "custo_call": call_escolhida["preco_medio"],  # Mudança para preço médio
                        "strike_put": put_escolhida["preco_exercicio"],
                        "custo_put": put_escolhida["preco_medio"],   # Mudança para preço médio
                        "vencimento_alvo": call_escolhida["data_vencimento"]
                    }
                    em_operacao = True
                    
        else:
            dias_para_vencer = (operacao_atual["vencimento_alvo"] - data_atual).days
            
            # Sai se o preço da ação alcançar o strike da opção OTM
            atingiu_strike_call = preco_acao_hoje >= operacao_atual["strike_call"]
            atingiu_strike_put = preco_acao_hoje <= operacao_atual["strike_put"]
            atingiu_tempo_limite = dias_para_vencer <= dias_limite_saida
            
            if atingiu_strike_call or atingiu_strike_put or atingiu_tempo_limite:
                # Localiza a linha exata das opções no dia do fechamento para capturar o preço médio de saída
                opcao_call_saida = dados_do_dia[dados_do_dia["cod_negociacao"] == operacao_atual["ticker_call"]]
                opcao_put_saida = dados_do_dia[dados_do_dia["cod_negociacao"] == operacao_atual["ticker_put"]]
                
                # Se a opção não teve negócio no dia da saída, assume o último preço médio disponível ou zero
                venda_call = opcao_call_saida["preco_medio"].iloc[0] if not opcao_call_saida.empty else 0
                venda_put = opcao_put_saida["preco_medio"].iloc[0] if not opcao_put_saida.empty else 0
                
                operacao_atual["data_saida"] = data_atual
                operacao_atual["preco_acao_saida"] = preco_acao_hoje
                operacao_atual["venda_call"] = venda_call
                operacao_atual["venda_put"] = venda_put
                
                # Cálculo do resultado financeiro simplificado (Venda - Compra)
                operacao_atual["resultado_call"] = venda_call - operacao_atual["custo_call"]
                operacao_atual["resultado_put"] = venda_put - operacao_atual["custo_put"]
                operacao_atual["resultado_total"] = operacao_atual["resultado_call"] + operacao_atual["resultado_put"]
                
                operacao_atual["motivo_saida"] = "Tempo" if atingiu_tempo_limite else "Preco"
                
                trades.append(operacao_atual)
                em_operacao = False

    return pd.DataFrame(trades)

if __name__ == "__main__":
    print("Executando o motor de backtest (isso pode levar alguns instantes)...")
    df_resultados = rodar_backtest_atualizado(df_final)
    
    if df_resultados.empty:
        print("Nenhuma operação foi concluída no período.")
    else:
        # Ordenar cronologicamente pela saída para garantir o gráfico acumulado correto
        df_resultados = df_resultados.sort_values("data_saida")
        df_resultados["pnl_acumulado"] = df_resultados["resultado_total"].cumsum()
        
        # Exibe um resumo básico no terminal
        print("\n--- Resumo do Backtest ---")
        print(f"Total de Operações: {len(df_resultados)}")
        print(f"Lucro Total Acumulado: R$ {df_resultados['resultado_total'].sum():.2f} (por par de opções)")
        print(f"Taxa de Acerto (Gain): {(df_resultados['resultado_total'] > 0).mean() * 100:.2f}%")
        
        # Plotagem dos gráficos
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
        
        # Gráfico 1: PnL Acumulado (Evolução Patrimonial)
        ax1.plot(df_resultados["data_saida"], df_resultados["pnl_acumulado"], marker='o', linestyle='-', color='#1f77b4')
        ax1.set_title("Evolução do PnL Acumulado")
        ax1.set_ylabel("PnL Acumulado (R$)")
        ax1.grid(True, linestyle='--', alpha=0.7)
        
        # Gráfico 2: Distribuição de Lucros e Prejuízos por Trade
        cores = ['#2ca02c' if x > 0 else '#d62728' for x in df_resultados["resultado_total"]]
        # O width depende da densidade de datas. Se houver muitos trades próximos, width=2 dias é bom visualmente.
        ax2.bar(df_resultados["data_saida"], df_resultados["resultado_total"], color=cores, width=pd.Timedelta(days=2))
        ax2.set_title("Resultado por Operação")
        ax2.set_ylabel("Resultado Individual (R$)")
        ax2.set_xlabel("Data de Saída")
        ax2.axhline(0, color='black', linewidth=1)
        ax2.grid(True, linestyle='--', alpha=0.7, axis='y')
        
        plt.tight_layout()
        plt.show()