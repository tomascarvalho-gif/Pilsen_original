
import os
import numpy as np

# Paths
path_1200 = '/Users/tomasdefreitascarvalho/Desktop/Work Space/Rubens/synapsee/Tunad/Videos_30_e_1200/videos1200'
path_audio = '/Users/tomasdefreitascarvalho/Desktop/Work Space/Rubens/synapsee/Tunad/Audios Tunad/videos/attentiveai'

# Get hashes from videos1200
files_1200 = [f for f in os.listdir(path_1200) if f.endswith('.npy')]
hashes_1200 = set([f.split('.')[0] for f in files_1200])

# Get hashes from Audios Tunad
files_audio = [f for f in os.listdir(path_audio) if f.endswith('.npy')]
hashes_audio = set([f.split('.')[0] for f in files_audio])

# Intersection
intersection = hashes_1200.intersection(hashes_audio)

print(f"Hashes in videos1200: {len(hashes_1200)}")
print(f"Hashes in Audios Tunad: {len(hashes_audio)}")
print(f"Intersection: {len(intersection)}")

# Check dtype of one file from videos1200
sample_file_1200 = os.path.join(path_1200, files_1200[0])
data_1200 = np.load(sample_file_1200, allow_pickle=True)
print(f"Sample 1200 shape: {data_1200.shape}")
print(f"Sample 1200 dtype: {data_1200.dtype}")

# Check content of one file from Audios Tunad
if len(files_audio) > 0:
    sample_file_audio = os.path.join(path_audio, files_audio[0])
    data_audio = np.load(sample_file_audio, allow_pickle=True)
    print(f"Sample Audio shape: {data_audio.shape}")
    print(f"Sample Audio dtype: {data_audio.dtype}")
