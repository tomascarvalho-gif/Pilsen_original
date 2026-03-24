import numpy as np
import matplotlib.pyplot as plt
import os

# Use non-interactive backend
plt.switch_backend('Agg')

file_path = '/Users/tomasdefreitascarvalho/Desktop/Work Space/Rubens/synapsee/Tunad/Audios Tunad/videos/00a1baac44ab42a5c926c549c9c3809d.mp4.npy'
output_file = '/Users/tomasdefreitascarvalho/Desktop/Work Space/Rubens/synapsee/video_data_visualization.png'

if not os.path.exists(file_path):
    print(f"Error: File not found at {file_path}")
else:
    try:
        data = np.load(file_path)
        
        plt.figure(figsize=(10, 6))
        plt.plot(data, marker='o', linestyle='-', color='b')
        plt.title('Data Visualization from .npy file')
        plt.xlabel('Index')
        plt.ylabel('Value')
        plt.grid(True)
        
        plt.savefig(output_file)
        print(f"Graph saved to: {output_file}")
        
    except Exception as e:
        print(f"An error occurred: {e}")
