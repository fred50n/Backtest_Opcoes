import pandas as pd

# 2. Motor do Backtest Modificado
def rodar_backtest_atualizado(df):
    trades = []
    em_operacao = False
    
    dias_limite_saida = 7
    margem_strike = 0.04
    liquidez_minima = 500000.0  # R$ 500 Mil
    
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
            # Localiza as opções no dia atual para verificar o preço de abertura
            opcao_call_atual = dados_do_dia[dados_do_dia["cod_negociacao"] == operacao_atual["ticker_call"]]
            opcao_put_atual = dados_do_dia[dados_do_dia["cod_negociacao"] == operacao_atual["ticker_put"]]
            
            # Se a opção não tem negócio no dia, assumimos valor ZERO (virou pó / sem liquidez) para registrar a perda
            abertura_call = opcao_call_atual["preco_abertura"].iloc[0] if not opcao_call_atual.empty else 0.0
            abertura_put = opcao_put_atual["preco_abertura"].iloc[0] if not opcao_put_atual.empty else 0.0

            # Verifica variação de 100% (dobrou de preço em relação ao custo de entrada)
            atingiu_alvo_call = abertura_call >= (2 * operacao_atual["custo_call"])
            atingiu_alvo_put = abertura_put >= (2 * operacao_atual["custo_put"])
            
            dias_para_vencer = (pd.to_datetime(operacao_atual["vencimento_alvo"]) - pd.to_datetime(data_atual)).days
            atingiu_tempo_limite = dias_para_vencer <= dias_limite_saida
            
            if atingiu_alvo_call or atingiu_alvo_put or atingiu_tempo_limite:
                operacao_atual["data_saida"] = data_atual
                operacao_atual["preco_acao_saida"] = preco_acao_hoje # Apenas para registro
                
                # Saída é feita pelo preço de abertura do dia
                operacao_atual["venda_call"] = abertura_call
                operacao_atual["venda_put"] = abertura_put
                
                operacao_atual["resultado_call"] = abertura_call - operacao_atual["custo_call"]
                operacao_atual["resultado_put"] = abertura_put - operacao_atual["custo_put"]
                operacao_atual["resultado_total"] = operacao_atual["resultado_call"] + operacao_atual["resultado_put"]
                
                operacao_atual["motivo_saida"] = "Tempo" if atingiu_tempo_limite and not (atingiu_alvo_call or atingiu_alvo_put) else "Alvo 100%"
                
                trades.append(operacao_atual)
                em_operacao = False

    return pd.DataFrame(trades)

if __name__ == "__main__":
    print("Carregando 'dados_tratados.csv'...")
    try:
        df_final = pd.read_csv("dados_tratados.csv", parse_dates=["data_pregao", "data_vencimento"])
    except FileNotFoundError:
        print("Arquivo 'dados_tratados.csv' não encontrado. Execute primeiro o script 01_tratamento_dados.py.")
        exit(1)
        
    print("Executando o motor de backtest (isso pode levar alguns instantes)...")
    df_resultados = rodar_backtest_atualizado(df_final)
    
    if df_resultados.empty:
        print("Nenhuma operação foi concluída no período.")
    else:
        print("Salvando resultados em 'resultados_backtest.csv'...")
        df_resultados.to_csv("resultados_backtest.csv", index=False)
        print("Concluído!")
