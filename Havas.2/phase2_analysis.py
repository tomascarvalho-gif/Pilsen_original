import pandas as pd
import numpy as np
from scipy.stats import pearsonr
import os
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

# Configuration
BASE_DIR = "/Users/tomasdefreitascarvalho/Desktop/Work Space/Rubens/synapsee/Havas.2"
OUTPUT_DIR = os.path.join(BASE_DIR, "phase2_output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

IMAGES_FILE = os.path.join(BASE_DIR, "Dados_Creatives_Enriched_Q1_2026_Phase1_Images_Only.csv")
VIDEOS_FILE = os.path.join(BASE_DIR, "Dados_Creatives_Enriched_Q1_2026_Phase1_Videos_Only.csv")

def analyze_group(df, variables, group_name):
    # This will store the text output
    lines = []
    lines.append(f"--- Analysis for: {group_name} ---")
    lines.append(f"Sample Size: {len(df)}")
    
    if len(df) < 10:
        lines.append("Not enough data to run correlations.\n")
        return "\n".join(lines)
        
    for target in ['CTR', 'clicks']:
        if target not in df.columns:
            continue
        lines.append(f"\nCorrelations with {target}:")
        
        # We need variance in target
        if df[target].std() == 0:
             lines.append("Target has zero variance. Skipping.")
             continue
             
        for var in variables:
            if var not in df.columns:
                continue
            
            clean_df = df[[var, target]].replace([np.inf, -np.inf], np.nan).dropna()
            # Require at least 10 data points and some variance to calculate pearsonr
            if len(clean_df) < 10:
                continue
            if clean_df[var].std() == 0 or clean_df[target].std() == 0:
                continue
                
            r, p = pearsonr(clean_df[var], clean_df[target])
            lines.append(f"  {var}: r = {r:.4f}, p = {p:.4f}")
            
            # Plot only if statistically significant and moderately strong to avoid thousands of plots
            if p < 0.05 and abs(r) >= 0.15: 
                # Clean filename
                safe_name = group_name.replace(' ', '_').replace('/', '_')
                plot_filename = f"scatter_{safe_name}_{var}_vs_{target}.png"
                plot_path = os.path.join(OUTPUT_DIR, plot_filename)
                
                plt.figure(figsize=(6, 4))
                sns.regplot(data=clean_df, x=var, y=target, scatter_kws={'alpha':0.5}, line_kws={"color": "red"})
                plt.title(f"{group_name}\n{var} vs {target} (r={r:.2f}, p={p:.3f})")
                plt.tight_layout()
                plt.savefig(plot_path)
                plt.close()
                lines.append(f"    * Generated plot: {plot_filename}")
                
    # Quartile analysis for CTR
    if 'CTR' in df.columns and len(df) >= 20:
        lines.append("\nQuartile Analysis on CTR:")
        q75 = df['CTR'].quantile(0.75)
        q25 = df['CTR'].quantile(0.25)
        top_group = df[df['CTR'] >= q75]
        bot_group = df[df['CTR'] <= q25]
        
        for var in variables:
            if var in df.columns:
                # Need to check if column is completely NaN
                if not bot_group[var].dropna().empty and bot_group[var].notna().any():
                     mean_bot = bot_group[var].mean()
                else: 
                     mean_bot = np.nan
                     
                if not top_group[var].dropna().empty and top_group[var].notna().any():
                     mean_top = top_group[var].mean()
                else: 
                     mean_top = np.nan
                     
                if not np.isnan(mean_bot) and not np.isnan(mean_top):
                     diff = mean_top - mean_bot
                     lines.append(f"  {var}: Bottom 25% CTR Mean = {mean_bot:.2f} | Top 25% CTR Mean = {mean_top:.2f} | Diff = {diff:.2f}")

    lines.append("\n")
    return "\n".join(lines)

def run_suite(suite_name, data_file, variables):
    print(f"Running {suite_name}...")
    df = pd.read_csv(data_file)
    output_text = []
    
    # 1. Global
    output_text.append(analyze_group(df, variables, f"{suite_name}_Global"))
    
    # 2. Trimester
    if 'trimester' in df.columns:
        for trim in df['trimester'].unique():
            if trim != 'Unknown':
                sub_df = df[df['trimester'] == trim]
                output_text.append(analyze_group(sub_df, variables, f"{suite_name}_Trimester_{trim}"))
                
    # 3. Cost Interval
    if 'cost_interval' in df.columns:
        for cost in df['cost_interval'].unique():
             if cost != 'Unknown':
                 sub_df = df[df['cost_interval'] == cost]
                 output_text.append(analyze_group(sub_df, variables, f"{suite_name}_Cost_{cost}"))
                 
    # 4. Trimester x Cost
    if 'trimester' in df.columns and 'cost_interval' in df.columns:
        for trim in df['trimester'].unique():
            if trim == 'Unknown': continue
            for cost in df['cost_interval'].unique():
                if cost == 'Unknown': continue
                sub_df = df[(df['trimester'] == trim) & (df['cost_interval'] == cost)]
                output_text.append(analyze_group(sub_df, variables, f"{suite_name}_{trim}_{cost}"))
                
    with open(os.path.join(OUTPUT_DIR, f"{suite_name}_Results.txt"), "w") as f:
        f.write("\n".join(output_text))
    print(f"Saved {suite_name} results.")

def main():
    img_vars = ['engajamentoneural', 'cognitivedemand', 'focus', 'fluency_index']
    vid_global_vars = ['engajamentoneural', 'cognitivedemand', 'focus', 'fluency_index']
    vid_timeline_vars = [
         'engajamentoneural_5sec', 'cognitivedemand_5sec', 'focus_5sec',
         'engajamentoneural_last_5sec', 'cognitivedemand_last_5sec', 'focus_last_5sec'
    ]
    
    run_suite("TEST_SUITE_A_Images", IMAGES_FILE, img_vars)
    run_suite("TEST_SUITE_B_Videos_Global", VIDEOS_FILE, vid_global_vars)
    run_suite("TEST_SUITE_C_Videos_Timeline", VIDEOS_FILE, vid_timeline_vars)
    
    print("\nPhase 2 Complete! Results are in 'phase2_output/' folder.")

if __name__ == "__main__":
    main()
