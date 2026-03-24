import numpy as np
import os

file_path = '/Users/tomasdefreitascarvalho/Desktop/Work Space/Rubens/synapsee/Tunad/Audios Tunad/videos/00a1baac44ab42a5c926c549c9c3809d.mp4.npy'

if not os.path.exists(file_path):
    print(f"Error: File not found at {file_path}")
else:
    try:
        data = np.load(file_path)
        print(f"Shape of the array: {data.shape}")
        print("\nFirst 10 rows of data:")
        print(data[:10])
    except Exception as e:
        print(f"An error occurred while loading the file: {e}")
