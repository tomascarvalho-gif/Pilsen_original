
import pandas as pd
import pickle
import os

excel_path = 'Tunad/Videos_db_Tunad/Audios Tunad ATUALIZADO.xlsx'
pickle_path = 'GAIA/results.pickle'

try:
    df = pd.read_excel(excel_path)
    print(f"Loaded Excel with {len(df)} rows")
    
    with open(pickle_path, 'rb') as f:
        results = pickle.load(f)
    print(f"Loaded pickle with {len(results)} keys")
    
    # helper to clean keys
    def clean_key(k):
        return os.path.basename(k) # remove path components

    pickle_keys = [clean_key(k) for k in results.keys()]
    excel_titles = df['Title'].astype(str).tolist()
    
    matches = 0
    for mk in pickle_keys:
        # fuzzy match or direct match?
        # Try direct match first (assuming Title is the filename)
        if mk in excel_titles:
            matches += 1
        else:
            # Try matching removing extension from pickle key if title has no extension
            if mk.endswith('.mp4'):
                 if mk[:-4] in excel_titles:
                     matches += 1
    
    print(f"Found {matches} matches out of {len(pickle_keys)} pickle keys")
    
    # Print some examples
    print("Example Pickle Keys (Cleaned):", pickle_keys[:5])
    print("Example Excel Titles:", excel_titles[:5])

except Exception as e:
    print(f"Error: {e}")
