
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt

# Paths
input_csv = 'Tunad/Videos_db_Tunad/Audios_Tunad_With_Fluency.csv'
output_report = 'Tunad/Videos_db_Tunad/Correlation_Report.md'

def classify_video(row):
    tags = str(row['Tags']).lower()
    title = str(row['Title']).lower()
    
    # Heuristics
    if 'performance' in tags or 'oferta' in tags or 'varejo' in tags or 'promoção' in tags:
        return 'Performance'
    if 'branding' in tags or 'institucional' in tags or 'manifesto' in tags:
        return 'Branding'
    
    # Fallback to Title
    if 'oferta' in title or 'promo' in title or '% off' in title:
        return 'Performance'
        
    return 'Uncategorized'

def analyze():
    print("Loading data...")
    df = pd.read_csv(input_csv)
    
    # Filter valid data
    df = df.dropna(subset=['Average_Neural', 'Average_Focus', 'Fluency_Index', 'AvgLift'])
    print(f"Analyzable rows: {len(df)}")
    
    # Classify
    df['Category'] = df.apply(classify_video, axis=1)
    print("Category Counts:")
    print(df['Category'].value_counts())
    
    # Metrics to correlate
    metrics = ['Average_Neural', 'Average_Focus', 'Fluency_Index', 'Peak_Score']
    target = 'AvgLift'
    
    results = []
    
    # Global Correlation
    print("\n--- Global Correlation ---")
    global_corr = df[metrics + [target]].corr(method='pearson')[target].drop(target)
    print(global_corr)
    results.append(f"## Global Correlations (n={len(df)})\n")
    results.append(global_corr.to_markdown())
    
    # Segmented Correlation
    for cat in ['Branding', 'Performance']:
        print(f"\n--- {cat} Correlation ---")
        sub_df = df[df['Category'] == cat]
        if len(sub_df) > 5:
            cat_corr = sub_df[metrics + [target]].corr(method='pearson')[target].drop(target)
            print(cat_corr)
            results.append(f"\n## {cat} Correlations (n={len(sub_df)})\n")
            results.append(cat_corr.to_markdown())
        else:
            print(f"Not enough samples for {cat} ({len(sub_df)})")
            results.append(f"\n## {cat} Correlations\n*Not enough samples (n={len(sub_df)})*")

    # Write Report
    with open(output_report, 'w') as f:
        f.write("# Unified Correlation Analysis Report\n\n")
        f.write("Analysis of Neural Metrics vs AvgLift.\n\n")
        for line in results:
            f.write(line + "\n")
            
    print(f"\nReport saved to {output_report}")

if __name__ == "__main__":
    analyze()
