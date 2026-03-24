
import pickle
import pandas as pd

path = '/Users/tomasdefreitascarvalho/Desktop/Work Space/Rubens/synapsee/Tunad/Videos_30_e_1200/videos.pickle'

try:
    with open(path, 'rb') as f:
        data = pickle.load(f)
    print(f"Type: {type(data)}")
    if isinstance(data, pd.DataFrame):
        print(f"Columns: {data.columns.tolist()}")
        print(f"Shape: {data.shape}")
        print(data.head())
    else:
        print(data)
except Exception as e:
    print(f"Error: {e}")
