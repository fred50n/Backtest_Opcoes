import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import math

def formatar_br(valor, casas=2):
    if pd.isna(valor):
        return ""
    # Formata com vírgula como decimal e ponto como milhar
    return f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")

# Configuracao da pagina
st.set_page_config(page_title="Dashboard Backtest", layout="wide")

@st.cache_data
def carregar_dados():
    try:
        df = pd.read_csv("dados_tratados.csv", parse_dates=["data_pregao", "data_vencimento"])
        return df
    except FileNotFoundError:
        st.error("Arquivo 'dados_tratados.csv' não encontrado. Execute o tratamento de dados primeiro.")
        return pd.DataFrame()

def rodar_backtest(df, margem_strike, dias_limite_saida, percentual_alvo, capital_por_operacao, dias_apos_vencimento):
    trades = []
    em_operacao = False
    ultimo_vencimento_operado = None
    liquidez_minima = 500000.0  # R$ 500 Mil
    
    datas_pregao = df["data_pregao"].sort_values().unique()
    datas_venc = df["data_vencimento"].dropna().unique()
    
    for data_atual in datas_pregao:
        dados_do_dia = df[df["data_pregao"] == data_atual]
        if dados_do_dia.empty:
            continue
            
        preco_acao_hoje = dados_do_dia["preco_acao"].iloc[0]
        
        if not em_operacao:
            # Lógica para identificar a entrada em relação ao último vencimento
            vencimentos_passados = datas_venc[datas_venc < data_atual]
            if len(vencimentos_passados) == 0:
                continue
                
            ultimo_vencimento = vencimentos_passados.max()
            dias_desde_vencimento = (data_atual - ultimo_vencimento).days
            
            condicao_entrada_valida = (dias_desde_vencimento >= dias_apos_vencimento) and (ultimo_vencimento_operado != ultimo_vencimento)
            
            if condicao_entrada_valida:
                alvo_call = preco_acao_hoje * (1 + margem_strike)
                alvo_put = preco_acao_hoje * (1 - margem_strike)
                
                calls_dia = dados_do_dia[(dados_do_dia["tipo_mercado"] == 70) & (dados_do_dia["volume_total"] >= liquidez_minima)]
                puts_dia = dados_do_dia[(dados_do_dia["tipo_mercado"] == 80) & (dados_do_dia["volume_total"] >= liquidez_minima)]
                
                if not calls_dia.empty and not puts_dia.empty:
                    call_escolhida = calls_dia.iloc[(calls_dia["preco_exercicio"] - alvo_call).abs().argmin()]
                    put_escolhida = puts_dia.iloc[(puts_dia["preco_exercicio"] - alvo_put).abs().argmin()]
                    
                    custo_total_unidade = call_escolhida["preco_medio"] + put_escolhida["preco_medio"]
                    # Lote padrão B3 é 100. Calcula quantos lotes cabem no capital.
                    qtd_opcoes = math.floor(capital_por_operacao / custo_total_unidade / 100) * 100
                    if qtd_opcoes == 0:
                        qtd_opcoes = 100  # Compra pelo menos 1 lote se o capital for muito pequeno
                    
                    operacao_atual = {
                        "ticker_call": call_escolhida["cod_negociacao"],
                        "ticker_put": put_escolhida["cod_negociacao"],
                        "data_entrada": data_atual,
                        "preco_acao_entrada": preco_acao_hoje,
                        "strike_call": call_escolhida["preco_exercicio"],
                        "custo_call": call_escolhida["preco_medio"],
                        "strike_put": put_escolhida["preco_exercicio"],
                        "custo_put": put_escolhida["preco_medio"],
                        "vencimento_alvo": call_escolhida["data_vencimento"],
                        "quantidade": qtd_opcoes,
                        "capital_investido": qtd_opcoes * custo_total_unidade
                    }
                    em_operacao = True
                    ultimo_vencimento_operado = ultimo_vencimento
                    
        else:
            opcao_call_atual = dados_do_dia[dados_do_dia["cod_negociacao"] == operacao_atual["ticker_call"]]
            opcao_put_atual = dados_do_dia[dados_do_dia["cod_negociacao"] == operacao_atual["ticker_put"]]
            
            # Se a opção não tem negócio no dia, assumimos valor ZERO (virou pó / sem liquidez) para registrar a perda
            abertura_call = opcao_call_atual["preco_abertura"].iloc[0] if not opcao_call_atual.empty else 0.0
            abertura_put = opcao_put_atual["preco_abertura"].iloc[0] if not opcao_put_atual.empty else 0.0

            # Verifica variação percentual alvo em relação ao custo de entrada
            atingiu_alvo_call = abertura_call >= ((1 + percentual_alvo) * operacao_atual["custo_call"])
            atingiu_alvo_put = abertura_put >= ((1 + percentual_alvo) * operacao_atual["custo_put"])
            
            dias_para_vencer = (pd.to_datetime(operacao_atual["vencimento_alvo"]) - pd.to_datetime(data_atual)).days
            atingiu_tempo_limite = dias_para_vencer <= dias_limite_saida
            
            if atingiu_alvo_call or atingiu_alvo_put or atingiu_tempo_limite:
                operacao_atual["data_saida"] = data_atual
                operacao_atual["preco_acao_saida"] = preco_acao_hoje
                
                operacao_atual["venda_call"] = abertura_call
                operacao_atual["venda_put"] = abertura_put
                
                # Resultado financeiro real = (Preço Saída - Preço Entrada) * Quantidade
                operacao_atual["resultado_call"] = (abertura_call - operacao_atual["custo_call"]) * operacao_atual["quantidade"]
                operacao_atual["resultado_put"] = (abertura_put - operacao_atual["custo_put"]) * operacao_atual["quantidade"]
                operacao_atual["resultado_total"] = operacao_atual["resultado_call"] + operacao_atual["resultado_put"]
                
                operacao_atual["motivo_saida"] = "Tempo" if atingiu_tempo_limite and not (atingiu_alvo_call or atingiu_alvo_put) else f"Alvo {int(percentual_alvo*100)}%"
                
                trades.append(operacao_atual)
                em_operacao = False

    return pd.DataFrame(trades)

def main():
    st.title("Aplicação Interativa de Backtest de Opções")
    st.markdown("Altere os parâmetros do modelo e avalie os resultados instantaneamente.")
    
    df_dados = carregar_dados()
    if df_dados.empty:
        return
        
    st.sidebar.header("Parâmetros do Modelo")
    
    # Filtro de Ano
    df_dados["ano_pregao"] = df_dados["data_pregao"].dt.year
    anos_disponiveis = sorted(df_dados["ano_pregao"].unique())
    anos_selecionados = st.sidebar.multiselect("Filtrar por Ano", options=anos_disponiveis, default=anos_disponiveis)
    
    margem_strike = st.sidebar.slider("Margem do Strike (OTM)", min_value=0.01, max_value=0.20, value=0.05, step=0.01, format="%.2f")
    percentual_alvo = st.sidebar.slider("Percentual Alvo de Lucro", min_value=0.1, max_value=3.0, value=1.0, step=0.1, format="%.1f")
    dias_limite_saida = st.sidebar.slider("Dias Limite para Saída", min_value=1, max_value=20, value=5, step=1)
    dias_apos_vencimento = st.sidebar.slider("Dias p/ Entrada (Após Último Venc.)", min_value=0, max_value=20, value=5, step=1)
    capital_operacao = st.sidebar.number_input("Capital por Operação (R$)", min_value=100.0, max_value=1000000.0, value=5000.0, step=500.0)
    
    if st.sidebar.button("🚀 Rodar Backtest"):
        if not anos_selecionados:
            st.sidebar.warning("Selecione pelo menos um ano para rodar o teste.")
            st.stop()
            
        with st.spinner("Executando simulação de backtest..."):
            df_filtrado = df_dados[df_dados["ano_pregao"].isin(anos_selecionados)]
            df_res = rodar_backtest(df_filtrado, margem_strike, dias_limite_saida, percentual_alvo, capital_operacao, dias_apos_vencimento)
            
        if df_res.empty:
            st.warning("Nenhuma operação foi concluída com esses parâmetros.")
            if 'df_resultados' in st.session_state:
                del st.session_state['df_resultados']
        else:
            st.session_state['df_resultados'] = df_res

    if 'df_resultados' in st.session_state:
        df_resultados = st.session_state['df_resultados'].copy()
        df_resultados["data_saida"] = pd.to_datetime(df_resultados["data_saida"])
        df_resultados = df_resultados.sort_values("data_saida")
        df_resultados["pnl_acumulado"] = df_resultados["resultado_total"].cumsum()
        df_resultados["ano"] = df_resultados["data_saida"].dt.year
        
        # Secao 1: Resumo do Backtest
        st.subheader("📋 Resumo do Backtest")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total de Operações", formatar_br(len(df_resultados), 0))
        lucro_total = df_resultados['resultado_total'].sum()
        col2.metric("Lucro Total Acumulado", f"R$ {formatar_br(lucro_total, 2)}")
        taxa_acerto = (df_resultados["resultado_total"] > 0).mean() * 100
        col3.metric("Taxa de Acerto (Gain)", f"{formatar_br(taxa_acerto, 2)}%")
        
        if st.button("💾 Exportar Resultados para CSV na raiz do projeto"):
            df_resultados.to_csv("df_resultados_exportado.csv", index=False)
            st.success("✅ Arquivo 'df_resultados_exportado.csv' salvo com sucesso na pasta do projeto!")
        
        # Secao 2: Evolucao e Individuais
        st.subheader("Evolução Patrimonial e Resultados")
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
        
        # Formatadores para o Eixo Y
        fmt_y = ticker.FuncFormatter(lambda x, pos: formatar_br(x, 0))
        ax1.yaxis.set_major_formatter(fmt_y)
        ax2.yaxis.set_major_formatter(fmt_y)
        
        ax1.plot(df_resultados["data_saida"], df_resultados["pnl_acumulado"], marker='o', linestyle='-', color='#1f77b4')
        ax1.set_title("Evolução do PnL Acumulado")
        ax1.set_ylabel("PnL Acumulado (R$)")
        ax1.grid(True, linestyle='--', alpha=0.7)
        
        cores = ['#2ca02c' if x > 0 else '#d62728' for x in df_resultados["resultado_total"]]
        ax2.bar(df_resultados["data_saida"], df_resultados["resultado_total"], color=cores, width=pd.Timedelta(days=2))
        ax2.set_title("Resultado por Operação")
        ax2.set_ylabel("Resultado Individual (R$)")
        ax2.set_xlabel("Data de Saída")
        ax2.axhline(0, color='black', linewidth=1)
        ax2.grid(True, linestyle='--', alpha=0.7, axis='y')
        
        st.pyplot(fig)
        
        # Secao 3: Graficos de Pizza por Ano
        st.subheader("Análise Anual: Quantidade de Operações e Volume Financeiro")
        
        anos = sorted(df_resultados["ano"].unique())
        if len(anos) > 5:
            anos = anos[-5:] # Pegar apenas os ultimos 5 anos
            
        fig_pie1, axes_pie1 = plt.subplots(1, len(anos), figsize=(4 * len(anos), 4))
        fig_pie2, axes_pie2 = plt.subplots(1, len(anos), figsize=(4 * len(anos), 4))
        
        if len(anos) == 1:
            axes_pie1 = [axes_pie1]
            axes_pie2 = [axes_pie2]
            
        for idx, ano in enumerate(anos):
            df_ano = df_resultados[df_resultados["ano"] == ano]
            gains = df_ano[df_ano["resultado_total"] > 0]
            losses = df_ano[df_ano["resultado_total"] <= 0]
            
            # Gráfico de Quantidade
            qtd_gains = len(gains)
            qtd_losses = len(losses)
            
            if qtd_gains == 0 and qtd_losses == 0:
                axes_pie1[idx].text(0.5, 0.5, 'Sem dados', ha='center', va='center')
                axes_pie1[idx].axis('off')
            else:
                axes_pie1[idx].pie([qtd_gains, qtd_losses], labels=['Gain', 'Loss'], autopct=lambda pct: f"{pct:.1f}%".replace(".", ","), colors=['#2ca02c', '#d62728'], startangle=90)
            axes_pie1[idx].set_title(f"Qtd Op. ({ano})")
            
            # Gráfico Ponderado por Valor Financeiro
            val_gains = gains["resultado_total"].sum() if not gains.empty else 0
            val_losses = abs(losses["resultado_total"].sum()) if not losses.empty else 0
            
            if val_gains == 0 and val_losses == 0:
                axes_pie2[idx].text(0.5, 0.5, 'Sem dados', ha='center', va='center')
                axes_pie2[idx].axis('off')
            else:
                axes_pie2[idx].pie([val_gains, val_losses], labels=['Valor Gain', 'Valor Loss'], autopct=lambda pct: f"{pct:.1f}%".replace(".", ","), colors=['#2ca02c', '#d62728'], startangle=90)
            axes_pie2[idx].set_title(f"Vol Finan. ({ano})")
            
        st.markdown("**% de Operações (Gain vs Loss)**")
        st.pyplot(fig_pie1)
        
        st.markdown("**% Ponderada pelo Valor (R$ Ganho vs R$ Perdido)**")
        st.pyplot(fig_pie2)

if __name__ == "__main__":
    main()
