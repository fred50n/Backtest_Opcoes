import pandas as pd
import matplotlib.pyplot as plt

if __name__ == "__main__":
    print("Carregando 'resultados_backtest.csv'...")
    try:
        df_resultados = pd.read_csv("resultados_backtest.csv", parse_dates=["data_entrada", "data_saida", "vencimento_alvo"])
    except FileNotFoundError:
        print("Arquivo 'resultados_backtest.csv' não encontrado. Execute primeiro o script 02_backtest.py.")
        exit(1)
        
    if df_resultados.empty:
        print("O arquivo de resultados está vazio. Nenhuma operação para exibir.")
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
