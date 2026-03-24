
import pandas as pd

file_path = 'Tunad/Videos_db_Tunad/Audios_Tunad_With_Fluency.csv'
try:
    df = pd.read_csv(file_path, nrows=5)
    print("Columns:", df.columns.tolist())
    print("-" * 20)
    print(df[['Title', 'Tags', 'AdBrandName']].head())
except Exception as e:
    print(f"Error reading csv: {e}")
