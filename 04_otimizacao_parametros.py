import pandas as pd
import itertools
from app import rodar_backtest
import time

def calcular_metricas(df_res):
    if df_res.empty:
        return 0, 0, 0
    
    lucro_total = df_res['resultado_total'].sum()
    
    qtd_operacoes = len(df_res)
    qtd_gain = len(df_res[df_res['resultado_total'] > 0])
    taxa_acerto_qtd = (qtd_gain / qtd_operacoes) * 100 if qtd_operacoes > 0 else 0
    
    ganho_financeiro = df_res[df_res['resultado_total'] > 0]['resultado_total'].sum()
    perda_financeira = abs(df_res[df_res['resultado_total'] <= 0]['resultado_total'].sum())
    total_movimentado = ganho_financeiro + perda_financeira
    
    taxa_acerto_financeiro = (ganho_financeiro / total_movimentado) * 100 if total_movimentado > 0 else 0
    
    return lucro_total, taxa_acerto_qtd, taxa_acerto_financeiro

def main():
    print("Carregando dados...")
    df = pd.read_csv("dados_tratados.csv", parse_dates=["data_pregao", "data_vencimento"])
    
    # Filtrar últimos 12 meses
    data_max = df['data_pregao'].max()
    data_min = data_max - pd.DateOffset(months=12)
    df_12m = df[df['data_pregao'] >= data_min].copy()
    
    print(f"Período analisado: {data_min.date()} a {data_max.date()}")
    
    # Definindo a grade de parâmetros (ajuste conforme necessário)
    margens_strike = [0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10]
    percentuais_alvo = [0.5, 1.0, 1.5, 2.0]
    dias_limite_saida = [3, 4, 7, 8]
    dias_apos_vencimento = [3, 4, 5, 6, 7]
    capital_operacao = 10000.0
    
    combinacoes = list(itertools.product(margens_strike, percentuais_alvo, dias_limite_saida, dias_apos_vencimento))
    total_comb = len(combinacoes)
    
    print(f"Total de combinações a testar: {total_comb}")
    
    resultados = []
    
    start_time = time.time()
    for i, (margem, alvo, limite_saida, apos_venc) in enumerate(combinacoes):
        if i % 10 == 0 and i > 0:
            elapsed = time.time() - start_time
            print(f"Testando combinação {i}/{total_comb}... (Tempo decorrido: {elapsed:.1f}s)")
            
        df_res = rodar_backtest(df_12m, margem, limite_saida, alvo, capital_operacao, apos_venc)
        
        lucro, tx_acerto_qtd, tx_acerto_fin = calcular_metricas(df_res)
        
        resultados.append({
            'margem_strike': margem,
            'percentual_alvo': alvo,
            'dias_limite_saida': limite_saida,
            'dias_apos_vencimento': apos_venc,
            'lucro_total': lucro,
            'taxa_acerto_qtd': tx_acerto_qtd,
            'taxa_acerto_financeiro': tx_acerto_fin,
            'qtd_operacoes': len(df_res)
        })
        
    df_resultados_opt = pd.DataFrame(resultados)
    
    # Top 10 Lucro Total
    print("\n--- TOP 10: Maior Lucro Total Acumulado ---")
    top_lucro = df_resultados_opt.sort_values(by='lucro_total', ascending=False).head(10)
    print(top_lucro.to_string(index=False))
    
    # Top 10 Taxa Acerto Quantidade
    print("\n--- TOP 10: Maior % de Acerto por Operações ---")
    top_tx_qtd = df_resultados_opt[df_resultados_opt['qtd_operacoes'] > 5].sort_values(by='taxa_acerto_qtd', ascending=False).head(10)
    print(top_tx_qtd.to_string(index=False))
    
    # Top 10 Taxa Acerto Financeiro
    print("\n--- TOP 10: Maior % de Acerto Financeiro ---")
    top_tx_fin = df_resultados_opt[df_resultados_opt['qtd_operacoes'] > 5].sort_values(by='taxa_acerto_financeiro', ascending=False).head(10)
    print(top_tx_fin.to_string(index=False))
    
    df_resultados_opt.to_csv("resultado_otimizacao.csv", index=False)
    print("\nResultados completos salvos em 'resultado_otimizacao.csv'")

if __name__ == "__main__":
    main()
