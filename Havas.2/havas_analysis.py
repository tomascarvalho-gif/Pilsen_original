
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
import statsmodels.api as sm
from scipy.stats import pearsonr, spearmanr
import os

# Configuration
INPUT_FILE = "/Users/tomasdefreitascarvalho/Desktop/Work Space/Rubens/synapsee/Havas.2/Dados_Creatives_Enriched_Q1_2026.csv"
OUTPUT_DIR = "/Users/tomasdefreitascarvalho/Desktop/Work Space/Rubens/synapsee/Havas.2/analysis_output"

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

def load_data(filepath):
    print(f"Loading data from {filepath}...")
    df = pd.read_csv(filepath)
    print(f"Data loaded. Shape: {df.shape}")
    return df

def plot_scatter(df, x_col, y_col, subset_name):
    """
    Plots a scatter plot with regression line for a specific pair of variables.
    """
    plt.figure(figsize=(8, 6))
    sns.scatterplot(data=df, x=x_col, y=y_col, alpha=0.6)
    plt.title(f"{subset_name}: {x_col} vs {y_col}")
    
    # Handle NaNs for regression plot
    clean_df = df[[x_col, y_col]].dropna()
    if len(clean_df) > 1:
        sns.regplot(data=clean_df, x=x_col, y=y_col, scatter=False, color='red')
    
    filename = f"scatter_{subset_name}_{x_col}_vs_{y_col}.png"
    filepath = os.path.join(OUTPUT_DIR, filename)
    plt.savefig(filepath)
    plt.close()
    # print(f"Scatter plot saved to {filepath}")

def run_regression_analysis(df, subset_name, predictors):
    print(f"\n--- Regression ({subset_name}) ---")
    target = 'CTR'
    
    # Filter predictors to those present in DataFrame
    valid_predictors = [p for p in predictors if p in df.columns]
    
    analysis_df = df[[target] + valid_predictors].dropna()
    if len(analysis_df) < 10:
        print("Not enough data for parameters regression.")
        return

    X = analysis_df[valid_predictors]
    X = sm.add_constant(X)
    y = analysis_df[target]
    
    try:
        model = sm.OLS(y, X).fit()
        print(model.summary())
        
        # Save summary
        with open(os.path.join(OUTPUT_DIR, f"regression_{subset_name}.txt"), "w") as f:
            f.write(model.summary().as_text())
    except Exception as e:
        print(f"Regression failed: {e}")

def analyze_subset(df, subset_name):
    print(f"\n--- Analyzing Subset: {subset_name} ---")
    print(f"Records: {len(df)}")
    
    if len(df) < 10:
        print("Not enough data for analysis.")
        return

    # Basic Metrics
    neuro_metrics = ['engajamentoneural', 'cognitivedemand', 'focus', 'fluency_index']
    
    # Advanced Metrics (only relevant for Video mostly, but code can handle both if columns exist)
    advanced_metrics = [
        'engajamentoneural_5sec', 'cognitivedemand_5sec', 'focus_5sec',
        'engajamentoneural_peak', 'cognitivedemand_peak', 'focus_peak'
    ]
    
    # Combined list of metrics to check
    all_metrics = neuro_metrics + advanced_metrics
    
    # Filter to what is actually in the DF
    available_metrics = [m for m in all_metrics if m in df.columns]
    
    # 1. Correlation Matrix
    # Include CTR and Clicks
    cols_to_corr = available_metrics + ['CTR', 'clicks', 'impressions']
    # Filter only columns that exist
    cols_to_corr = [c for c in cols_to_corr if c in df.columns]
    
    analysis_df = df[cols_to_corr].dropna()
    if len(analysis_df) < 2:
         print("No valid data for correlation.")
         return

    corr_matrix = analysis_df.corr(method='pearson')
    
    # Save Heatmap
    plt.figure(figsize=(12, 10))
    sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', fmt=".2f")
    plt.title(f"Correlation Matrix ({subset_name})")
    heatmap_path = os.path.join(OUTPUT_DIR, f"heatmap_{subset_name}.png")
    plt.savefig(heatmap_path)
    plt.close()
    print(f"Heatmap saved to {heatmap_path}")

    # 2. Specific Correlations (Focus on CTR)
    print(f"\nCorrelations with CTR ({subset_name}):")
    for neuro in available_metrics:
        # Use the cleaned analysis_df to ensure matching lengths
        if neuro in analysis_df.columns and 'CTR' in analysis_df.columns:
            series_x = analysis_df[neuro]
            series_y = analysis_df['CTR']
            
            # Check for constant values to avoid warning/error
            if series_x.std() == 0 or series_y.std() == 0:
                print(f"  {neuro} vs CTR: Constant input, skipping.")
                continue
                
            r, p = pearsonr(series_x, series_y)
            print(f"  {neuro} vs CTR: r={r:.4f} (p={p:.4f})")
            
            # Plot significant or strong correlations
            if abs(r) > 0.05 or p < 0.05:
                plot_scatter(df, neuro, 'CTR', subset_name)

    # 3. Quartile Analysis
    # Compare Top 25% CTR vs Bottom 25% CTR
    try:
        if 'CTR' in df.columns and len(df) > 20:
            q75 = df['CTR'].quantile(0.75)
            q25 = df['CTR'].quantile(0.25)
            
            top_group = df[df['CTR'] >= q75]
            bottom_group = df[df['CTR'] <= q25]
            
            print(f"\nQuartile Analysis ({subset_name}):")
            print(f"Top 25% CTR threshold: {q75:.4f} (n={len(top_group)})")
            print(f"Bottom 25% CTR threshold: {q25:.4f} (n={len(bottom_group)})")
            
            comparison_results = []
            for metric in available_metrics:
                mean_top = top_group[metric].mean()
                mean_bottom = bottom_group[metric].mean()
                
                # Calculate diff
                if not np.isnan(mean_bottom) and mean_bottom != 0:
                    diff_pct = ((mean_top - mean_bottom) / mean_bottom) * 100
                else:
                    diff_pct = 0.0
                
                print(f"  {metric}: Top={mean_top:.2f}, Bottom={mean_bottom:.2f}, Diff={diff_pct:.2f}%")
                comparison_results.append({'metric': metric, 'Top': mean_top, 'Bottom': mean_bottom})
                
            # Plot Quartile Comparison
            comp_df = pd.DataFrame(comparison_results)
            if not comp_df.empty:
                comp_df_melted = comp_df.melt(id_vars='metric', value_vars=['Top', 'Bottom'], var_name='Group', value_name='Value')
                plt.figure(figsize=(12, 6))
                sns.barplot(data=comp_df_melted, x='metric', y='Value', hue='Group')
                plt.xticks(rotation=45)
                plt.title(f"Top vs Bottom 25% CTR Comparison ({subset_name})")
                plt.tight_layout()
                plt.savefig(os.path.join(OUTPUT_DIR, f"quartile_{subset_name}.png"))
                plt.close()
        else:
             print("Skipping Quartile analysis (insufficient data).")

    except Exception as e:
        print(f"Quartile analysis failed: {e}")

    # 4. Regression (All Metrics)
    run_regression_analysis(df, subset_name, predictors=available_metrics)
    
    # 5. XGBoost Analysis
    run_xgboost_analysis(df, subset_name, predictors=available_metrics)


def run_xgboost_analysis(df, subset_name, predictors):
    print(f"\n--- XGBoost Analysis ({subset_name}) ---")
    try:
        import xgboost as xgb
        from sklearn.metrics import r2_score, mean_squared_error
        from sklearn.model_selection import train_test_split
    except ImportError:
        print("XGBoost or Sklearn not installed. Skipping.")
        return

    target = 'CTR'
    valid_predictors = [p for p in predictors if p in df.columns]
    
    analysis_df = df[[target] + valid_predictors].dropna()
    if len(analysis_df) < 20:
        print("Not enough data for XGBoost.")
        return

    X = analysis_df[valid_predictors]
    y = analysis_df[target]
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Train
    model = xgb.XGBRegressor(objective='reg:squarederror', n_estimators=100, learning_rate=0.1, max_depth=3)
    model.fit(X_train, y_train)
    
    # Predict
    y_pred = model.predict(X_test)
    
    # Evaluate
    r2 = r2_score(y_test, y_pred)
    mse = mean_squared_error(y_test, y_pred)
    
    print(f"XGBoost R-squared: {r2:.4f}")
    print(f"XGBoost MSE: {mse:.4f}")
    
    # Feature Importance
    plt.figure(figsize=(10, 6))
    xgb.plot_importance(model, max_num_features=10)
    plt.title(f"XGBoost Feature Importance ({subset_name})")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, f"xgboost_importance_{subset_name}.png"))
    plt.close()
    
    # Save summary
    with open(os.path.join(OUTPUT_DIR, f"xgboost_{subset_name}.txt"), "w") as f:
        f.write(f"XGBoost Results ({subset_name}):\n")
        f.write(f"R-squared: {r2:.4f}\n")
        f.write(f"MSE: {mse:.4f}\n")



def main():
    df = load_data(INPUT_FILE)
    
    # Split into Video and Image
    df_video = df[df['video_public_storage_url'].notna()]
    df_image = df[df['video_public_storage_url'].isna()]
    
    print(f"Total Videos: {len(df_video)}")
    print(f"Total Images: {len(df_image)}")

    analyze_subset(df_video, "Video")
    analyze_subset(df_image, "Image")
    
    print("\nAnalysis complete.")

if __name__ == "__main__":
    main()
