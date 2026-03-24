import os
import json
import itertools
import matplotlib.pyplot as plt
import seaborn as sns

def load_embeddings(base_dir):
    all_embeddings = []
    
    # Load from images
    img_dir = os.path.join(base_dir, 'public_storage_url', 'indices')
    if os.path.exists(img_dir):
        for fname in os.listdir(img_dir):
            if fname.endswith('.json'):
                with open(os.path.join(img_dir, fname), 'r') as f:
                    data = json.load(f)
                    if 'embeddings' in data:
                        all_embeddings.extend(data['embeddings'])

    # Load from videos
    vid_dir = os.path.join(base_dir, 'video_public_storage_url', 'indices')
    if os.path.exists(vid_dir):
        for fname in os.listdir(vid_dir):
            if fname.endswith('.json'):
                with open(os.path.join(vid_dir, fname), 'r') as f:
                    data = json.load(f)
                    if 'embeddings' in data:
                        # Video embeddings is a list of lists (matrices)
                        for time_window in data['embeddings']:
                            all_embeddings.extend(time_window)

    return all_embeddings

def main():
    base_dir = '.'
    print("Loading embeddings from all json files...")
    embeddings = load_embeddings(base_dir)
    
    if not embeddings:
        print("No embeddings found!")
        return
        
    print(f"Loaded {len(embeddings)} individual embedding float values.")
    
    print("Basic Statistics:")
    print(f"Min: {min(embeddings):.4f}")
    print(f"Max: {max(embeddings):.4f}")
    print(f"Mean: {(sum(embeddings)/len(embeddings)):.4f}")
    
    # Plotting
    plt.figure(figsize=(10, 6))
    sns.histplot(embeddings, bins=50, kde=True, color='blue', edgecolor='black')
    
    plt.title('Distribution of Neural Embeddings (All Dimensions combined)')
    plt.xlabel('Embedding Value')
    plt.ylabel('Frequency')
    plt.grid(axis='y', alpha=0.75)
    
    output_file = 'embeddings_distribution.png'
    plt.savefig(output_file)
    print(f"Plot saved to: {output_file}")
    
if __name__ == '__main__':
    main()
