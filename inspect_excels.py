
import pandas as pd
import os

base_path = '/Users/tomasdefreitascarvalho/Desktop/Work Space/Rubens/synapsee/Tunad/Audios Tunad'

files = [
    'Audios Tunad - EngNeural.xlsx',
    'Audios Tunad ATUALIZADO - EngNeural.xlsx',
    'Tunad_Forebrain_Attention2Performance_Index.xlsx',
    'Audios Tunad.xlsx'
]

for file in files:
    path = os.path.join(base_path, file)
    print(f"\n--- Inspecting {file} ---")
    try:
        df = pd.read_excel(path, nrows=5)
        print(f"Columns: {df.columns.tolist()}")
        print(df.head())
    except Exception as e:
        print(f"Error reading {file}: {e}")
