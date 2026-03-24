
import pandas as pd

file_path = 'Tunad/Videos_db_Tunad/Audios Tunad ATUALIZADO.xlsx'
try:
    df = pd.read_excel(file_path, nrows=5)
    print("Row 0 VideoURL:", df['VideoURL'].iloc[0])
    print("Row 1 VideoURL:", df['VideoURL'].iloc[1])
except Exception as e:
    print(f"Error reading excel: {e}")
