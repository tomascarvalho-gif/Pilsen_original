
import pandas as pd

file_path = 'Tunad/Videos_db_Tunad/Audios_Tunad_With_Fluency.csv'
try:
    df = pd.read_csv(file_path)
    # Print first 10 non-null tags
    print("Sample Tags:")
    print(df['Tags'].dropna().head(10).tolist())
    
    # Check if 'Branding' or 'Performance' keywords exist in Tags
    all_tags = " ".join(df['Tags'].dropna().astype(str).tolist()).lower()
    print("\nKeywords Check:")
    print("branding" in all_tags)
    print("performance" in all_tags)
    print("oferta" in all_tags)
    print("institucional" in all_tags)
    
except Exception as e:
    print(f"Error: {e}")
