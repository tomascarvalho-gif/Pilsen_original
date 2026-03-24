import pandas as pd
import numpy as np
from scipy.stats import pearsonr

def load_and_prep_data():
    file_path = "Dados_Creatives_Enriched_Q1_2026_Videos_Only.csv"
    print(f"Loading {file_path}...")
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return None
        
    print(f"Original Video rows: {len(df)}")
    
    # 1. Cleaning Outliers (same logic as the phase2_analysis to keep things standardized)
    # Filter 1: Valid CTR and Clicks
    df = df[df['CTR'].notna() & (df['CTR'] > 0)]
    df = df[df['clicks'].notna() & (df['clicks'] > 0)]
    
    # Filter 2: Basic IQR Outlier Removal for CTR
    Q1 = df['CTR'].quantile(0.25)
    Q3 = df['CTR'].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    df = df[(df['CTR'] >= lower_bound) & (df['CTR'] <= upper_bound)]
    
    # Required columns for the historical test
    req_cols = [
        'CTR', 'engajamentoneural', 'cognitivedemand', 'focus',
        'engajamentoneural_5sec', 'cognitivedemand_5sec', 'focus_5sec'
    ]
    
    # Drop NaNs in required columns
    df = df.dropna(subset=req_cols)
    print(f"Rows after filtering (valid CTR/metrics): {len(df)}\n")
    return df

def run_correlation_test(df, target, features, test_name):
    print(f"--- Correlation Results ({test_name}) ---")
    print(f"Target: {target}")
    results = []
    for f in features:
        try:
            corr, p_value = pearsonr(df[f], df[target])
            significance = ""
            if p_value < 0.05:
                significance = "⭐ STATISTICALLY SIGNIFICANT"
            print(f"  {f+':':<25} r = {corr:>7.4f}, p = {p_value:>6.4f}  {significance}")
            results.append((f, corr, p_value))
        except Exception as e:
            print(f"  Error on {f}: {e}")
    print()
    return results

def run_quartile_test(df, target, features, test_name):
    print(f"--- Quartile Comparison ({test_name}) ---")
    print(f"Dividing into Top 25% vs Bottom 25% based on Target: {target}")
    
    top_thresh = df[target].quantile(0.75)
    bottom_thresh = df[target].quantile(0.25)
    
    top_df = df[df[target] >= top_thresh]
    bottom_df = df[df[target] <= bottom_thresh]
    
    print(f"Top 25% Group Size: {len(top_df)}, Bottom 25% Group Size: {len(bottom_df)}")
    
    for f in features:
        top_mean = top_df[f].mean()
        bottom_mean = bottom_df[f].mean()
        
        # Protect against div zero
        if bottom_mean != 0:
            diff_pct = ((top_mean - bottom_mean) / bottom_mean) * 100
        else:
            diff_pct = float('nan')
            
        trend = "📈 Higher in Top Performers" if top_mean > bottom_mean else "📉 Lower in Top Performers"
            
        print(f"  {f+':':<25} Top Mean = {top_mean:>6.2f} | Bottom Mean = {bottom_mean:>6.2f} | Diff = {diff_pct:>+6.1f}%  {trend}")
    print()

def main():
    df = load_and_prep_data()
    if df is None:
        return
        
    full_video_features = ['engajamentoneural', 'cognitivedemand', 'focus']
    first_5sec_features = ['engajamentoneural_5sec', 'cognitivedemand_5sec', 'focus_5sec']
    target_metric = 'CTR'
    
    # 1. Run Pearson Correlation identical to the 19/12 presentation
    run_correlation_test(df, target_metric, full_video_features, "Full Video (Média do vídeo todo)")
    run_correlation_test(df, target_metric, first_5sec_features, "Only First 5 Seconds (Hipótese dos 5 Segundos)")
    
    # 2. Run Quartile Comparision identical to the 07/12 presentation
    run_quartile_test(df, target_metric, full_video_features, "Full Video (Média do vídeo todo)")
    run_quartile_test(df, target_metric, first_5sec_features, "Only First 5 Seconds (Hipótese dos 5 Segundos)")

if __name__ == '__main__':
    main()
