
import pandas as pd
import numpy as np
from scipy.stats import pearsonr
import matplotlib.pyplot as plt
import seaborn as sns
import os

def analyze_tunad_fluency_excel():
    excel_path = '/Users/tomasdefreitascarvalho/Desktop/Work Space/Rubens/synapsee/Tunad/Audios Tunad/Audios Tunad ATUALIZADO - EngNeural.xlsx'
    
    print(f"Loading data from {excel_path}...")
    try:
        df = pd.read_excel(excel_path)
    except Exception as e:
        print(f"Error loading Excel: {e}")
        return

    print(f"Total rows: {len(df)}")
    
    # Required columns
    required_cols = ['EngNeural', 'Índice de Foco', 'TotalLift', 'AvgLift', 'AvgCallToAction']
    
    # Check if columns exist
    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        print(f"Missing columns: {missing_cols}")
        # Try to find similar columns if exact names don't match (e.g. casing)
        print("Available columns:", df.columns.tolist())
        return

    # Filter invalid data
    df_clean = df.dropna(subset=required_cols)
    print(f"Rows after dropping NaNs in required columns: {len(df_clean)}")
    
    # Calculate Fluency Index
    # Fluency = Neural Engagement / Focus
    # Ensure Focus is not 0 to avoid division by zero
    df_clean = df_clean[df_clean['Índice de Foco'] > 0]
    
    df_clean['Fluency_Index'] = df_clean['EngNeural'] / df_clean['Índice de Foco']
    
    print(f"Calculated Fluency Index for {len(df_clean)} rows.")
    
    # Correlation Analysis
    metrics_to_correlate = ['TotalLift', 'AvgLift', 'AvgCallToAction']
    neural_metrics = ['EngNeural', 'Índice de Foco', 'Fluency_Index']
    
    results = {}
    
    print("\n--- Correlation Results (Tunad - Audios) ---")
    for perf_metric in metrics_to_correlate:
        print(f"\nTarget: {perf_metric}")
        for neural in neural_metrics:
            try:
                corr, p_value = pearsonr(df_clean[neural], df_clean[perf_metric])
                results[f"{neural} vs {perf_metric}"] = (corr, p_value)
                print(f"  {neural}: Correlation = {corr:.3f}, p-value = {p_value:.3f}")
            except Exception as e:
                print(f"  Could not calculate for {neural}: {e}")

    # Visualizations
    plt.figure(figsize=(15, 5))
    
    # Engagement vs Lift
    plt.subplot(1, 3, 1)
    sns.regplot(x='EngNeural', y='TotalLift', data=df_clean, scatter_kws={'alpha':0.3}, line_kws={'color':'red'})
    plt.title('Neural Engagement vs Total Lift')
    
    # Focus vs Lift
    plt.subplot(1, 3, 2)
    sns.regplot(x='Índice de Foco', y='TotalLift', data=df_clean, scatter_kws={'alpha':0.3}, line_kws={'color':'green'})
    plt.title('Focus vs Total Lift')
    
    # Fluency vs Lift
    plt.subplot(1, 3, 3)
    sns.regplot(x='Fluency_Index', y='TotalLift', data=df_clean, scatter_kws={'alpha':0.3}, line_kws={'color':'blue'})
    plt.title('Fluency Index vs Total Lift')
    
    plt.tight_layout()
    plt.savefig('tunad_fluency_correlations_excel.png')
    print("\nSaved plot to tunad_fluency_correlations_excel.png")

    # Additional Check: Top vs Bottom performers
    # Define top 25% and bottom 25% based on AvgLift
    q75 = df_clean['AvgLift'].quantile(0.75)
    q25 = df_clean['AvgLift'].quantile(0.25)
    
    top_performers = df_clean[df_clean['AvgLift'] >= q75]
    bottom_performers = df_clean[df_clean['AvgLift'] <= q25]
    
    print("\n--- Group Comparison (Top 25% vs Bottom 25% AvgLift) ---")
    print(f"Top Group Size: {len(top_performers)}, Bottom Group Size: {len(bottom_performers)}")
    
    for metric in neural_metrics:
        top_mean = top_performers[metric].mean()
        bottom_mean = bottom_performers[metric].mean()
        diff_pct = ((top_mean - bottom_mean) / bottom_mean) * 100
        print(f"{metric}: Top Mean = {top_mean:.3f}, Bottom Mean = {bottom_mean:.3f}, Diff = {diff_pct:.1f}%")

if __name__ == "__main__":
    analyze_tunad_fluency_excel()
