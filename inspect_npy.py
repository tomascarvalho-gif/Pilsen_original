
import numpy as np
import os

# Pick a file that exists
npy_file = 'Tunad/Videos_30_e_1200/videos1200/fff9fcb83b26fb03df6c326cd52d8643.mp4.npy'

try:
    data = np.load(npy_file, allow_pickle=True)
    print(f"Shape: {data.shape}")
    print(f"Data Type: {data.dtype}")
    print(f"Content: {data}")
except Exception as e:
    print(f"Error: {e}")
