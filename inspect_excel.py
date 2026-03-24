
import pandas as pd

file_path = 'Tunad/Videos_db_Tunad/Audios Tunad ATUALIZADO.xlsx'
try:
    df = pd.read_excel(file_path, nrows=5)
    print(df.columns.tolist())
    print(df.head())
except Exception as e:
    print(f"Error reading excel: {e}")
