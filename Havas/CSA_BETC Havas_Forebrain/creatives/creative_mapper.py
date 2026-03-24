# """
# Creative Mapper - Maps CSV ad data to creative files in folder structure

# This script helps match ad performance data from CSV to the actual creative files
# stored in the folder hierarchy.
# """

import os
import csv
import re
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import defaultdict


class CreativeMapper:
    """Maps CSV ad data to creative files"""
    
    def __init__(self, creatives_base_path: str, save_output: bool = False):
        self.base_path = Path(creatives_base_path)
        self.file_cache = []
        self.save_output = save_output
        self.all_scores = []  # Track all scores for distribution analysis
        
        # Static mapping dictionaries for normalization
        self.PLATFORM_MAP = {
            'facebook': ['META', 'FACEBOOK'],
            'google': ['GOOGLE'],
            'instagram': ['META', 'INSTAGRAM'],
        }
        
        self.FORMAT_MAP = {
            'estatico': ['ESTÁTICAS', 'ESTATICAS'],
            'animado': ['ANIMADAS', 'ANIMAÇÃO'],
            'carrossel': ['CARROSSEL'],
            'catalogo': ['CATÁLOGO', 'CATALOGO'],
        }
        
        # Add more mappings as needed
        self.CRIATIVO_MAP = {
            'custo-beneficio': ['CUSTO BENEFÍCIO', 'CUSTO', 'BENEFICIO'],
            'chip-gratis': ['CHIP GRATIS', 'CHIPGRATIS'],
            'gb-preco': ['GB PREÇO', 'GBPREÇO'],
        }
        
    def build_file_cache(self):
        """Build a cache of all creative files with their paths"""
        print(f"🔍 Scanning creatives folder: {self.base_path}")
        
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        video_extensions = {'.mp4', '.mov', '.avi'}
        valid_extensions = image_extensions | video_extensions
        
        for root, dirs, files in os.walk(self.base_path):
            for file in files:
                file_path = Path(root) / file
                if file_path.suffix.lower() in valid_extensions:
                    dimension = self.extract_dimension(str(file_path))
                    self.file_cache.append({
                        'path': file_path,
                        'relative_path': file_path.relative_to(self.base_path),
                        'filename': file,
                        'path_str': str(file_path).lower(),
                        'parts': str(file_path).lower().split(os.sep),
                        'dimension': dimension
                    })
        
        print(f"✅ Found {len(self.file_cache)} creative files")
        
    def extract_dimension(self, path: str) -> Optional[str]:
        """
        Extract dimension from file path
        Example: '.../1080x1920/file.png' -> '1080x1920'
        """
        pattern = r'(\d{3,4})[xX](\d{3,4})'
        match = re.search(pattern, path)
        if match:
            return f"{match.group(1)}x{match.group(2)}"
        return None
    
    def get_base_path_without_dimension(self, file_path: str) -> str:
        """
        Remove dimension folder from path to group variants
        Example: '.../1080x1920/file.png' -> '.../file.png'
        """
        pattern = r'/(\d{3,4})[xX](\d{3,4})/'
        return re.sub(pattern, '/', file_path, count=1)
    
    def normalize_criativo(self, criativo: str) -> List[str]:
        """
        Normalize criativo name to searchable keywords
        Example: 'kv-custo-beneficio' -> ['custo', 'beneficio', 'kv']
        """
        # Remove common prefixes
        criativo = criativo.replace('kv-', '').replace('pais-', '')
        
        # Split by hyphens and underscores
        parts = re.split(r'[-_]', criativo)
        
        # Create variations
        keywords = []
        for part in parts:
            keywords.append(part)
            # Add version without numbers (v2, v3, etc)
            clean_part = re.sub(r'v\d+', '', part)
            if clean_part and clean_part != part:
                keywords.append(clean_part)
        
        return [k for k in keywords if len(k) > 1]  # Filter very short keywords
    
    def extract_gb_amount(self, oferta: str) -> str:
        """
        Extract GB amount from oferta
        Example: '27gb-38m' -> '27'
        """
        match = re.search(r'(\d+)gb', oferta.lower())
        return match.group(1) if match else None
    
    def calculate_match_score(self, csv_row: Dict, file_info: Dict) -> float:
        """
        Calculate match score between CSV row and file
        Returns score from 0.0 to 1.0
        """
        score = 0.0
        path_str = file_info['path_str']
        parts = file_info['parts']
        
        # 1. Check platform (facebook -> META)
        platform = csv_row['Veículo'].lower()
        if platform in self.PLATFORM_MAP:
            for platform_variant in self.PLATFORM_MAP[platform]:
                if platform_variant.lower() in path_str:
                    score += 0.2
                    break
        
        # 2. Check GB amount (27gb-38m -> 27GB)
        gb_amount = self.extract_gb_amount(csv_row['Oferta'])
        if gb_amount:
            if f'{gb_amount}gb' in path_str or f'{gb_amount} gb' in path_str:
                score += 0.2
        
        # 3. Check format (estatico -> ESTÁTICAS)
        formato = csv_row['Formato'].lower()
        if formato in self.FORMAT_MAP:
            for format_variant in self.FORMAT_MAP[formato]:
                if format_variant.lower() in path_str:
                    score += 0.2
                    break
        
        # 4. Check criativo keywords (kv-custo-beneficio -> CUSTO BENEFÍCIO)
        criativo_keywords = self.normalize_criativo(csv_row['Criativo'])
        matched_keywords = 0
        for keyword in criativo_keywords:
            if keyword.lower() in path_str:
                matched_keywords += 1
        
        if criativo_keywords:
            keyword_score = matched_keywords / len(criativo_keywords)
            score += 0.3 * keyword_score
        
        # 5. Check campaign (asc, migracao, etc)
        campanha = csv_row['Campanha'].lower()
        if campanha in path_str:
            score += 0.1
        
        return score
    
    def find_best_match(self, csv_row: Dict, top_n: int = 5) -> List[Dict]:
        """
        Find best matching files for a CSV row
        Returns list of top N matches with scores
        """
        matches = []
        
        for file_info in self.file_cache:
            score = self.calculate_match_score(csv_row, file_info)
            if score > 0:  # Only include files with some match
                matches.append({
                    'file': file_info['relative_path'],
                    'score': score,
                    'path': file_info['path'],
                    'dimension': file_info.get('dimension', 'unknown')
                })
                self.all_scores.append(score)  # Track for distribution
        
        # Sort by score descending
        matches.sort(key=lambda x: x['score'], reverse=True)
        
        return matches[:top_n]
    
    def group_by_dimension(self, matches: List[Dict]) -> Dict[float, List[Dict]]:
        """
        Group matches by base path (same creative, different dimensions)
        Returns dict: {score: [list of dimension variants]}
        """
        grouped = defaultdict(list)
        
        for match in matches:
            base_path = self.get_base_path_without_dimension(str(match['file']))
            grouped[base_path].append(match)
        
        # Return groups with their scores
        result = {}
        for base_path, variants in grouped.items():
            if variants:
                # Use the score from the first variant (they should be the same)
                score = variants[0]['score']
                result[score] = variants
        
        return result
    
    def print_match_results(self, csv_row: Dict, matches: List[Dict], show_grouped: bool = True):
        """Print matching results in a readable format"""
        print("\n" + "="*80)
        print("🎯 MATCHING RESULTS")
        print("="*80)
        
        print("\n📊 CSV Data:")
        print(f"  Ad Name: {csv_row.get('real_ad_name', 'N/A')}")
        print(f"  Veículo: {csv_row['Veículo']}")
        print(f"  Campanha: {csv_row['Campanha']}")
        print(f"  Oferta: {csv_row['Oferta']}")
        print(f"  Criativo: {csv_row['Criativo']}")
        print(f"  Formato: {csv_row['Formato']}")
        
        print("\n🔍 Search Strategy:")
        print(f"  Platform mapping: {csv_row['Veículo']} -> {self.PLATFORM_MAP.get(csv_row['Veículo'].lower(), 'N/A')}")
        print(f"  GB amount: {self.extract_gb_amount(csv_row['Oferta'])}")
        print(f"  Format mapping: {csv_row['Formato']} -> {self.FORMAT_MAP.get(csv_row['Formato'].lower(), 'N/A')}")
        print(f"  Criativo keywords: {self.normalize_criativo(csv_row['Criativo'])}")
        
        if show_grouped:
            # Group by dimension variants
            grouped = self.group_by_dimension(matches)
            
            print(f"\n📁 Grouped Results (by score, showing dimension variants):")
            if not grouped:
                print("  ❌ No matches found!")
            else:
                for i, (score, variants) in enumerate(sorted(grouped.items(), key=lambda x: x[0], reverse=True), 1):
                    print(f"\n  Group {i} - Score: {score:.2f} ({len(variants)} dimension variants)")
                    dimensions = [v['dimension'] for v in variants]
                    print(f"     Dimensions: {', '.join(dimensions)}")
                    print(f"     Base Path: {self.get_base_path_without_dimension(str(variants[0]['file']))}")
                    for variant in variants:
                        print(f"       └─ {variant['dimension']}: {variant['file'].name}")
        else:
            print(f"\n📁 Top {len(matches)} Matches:")
            if not matches:
                print("  ❌ No matches found!")
            else:
                for i, match in enumerate(matches, 1):
                    print(f"\n  {i}. Score: {match['score']:.2f} | Dimension: {match.get('dimension', 'N/A')}")
                    print(f"     Path: {match['file']}")
        
        print("\n" + "="*80)
    
    def plot_score_distribution(self):
        """Plot distribution of all scores to validate scoring algorithm"""
        if not self.all_scores:
            print("⚠️  No scores to plot yet")
            return
        
        plt.figure(figsize=(10, 4))
        
        # Histogram
        plt.subplot(1, 2, 1)
        plt.hist(self.all_scores, bins=20, edgecolor='black', alpha=0.7)
        plt.xlabel('Match Score')
        plt.ylabel('Frequency')
        plt.title('Score Distribution (All Matches)')
        plt.grid(True, alpha=0.3)
        
        # Box plot
        plt.subplot(1, 2, 2)
        plt.boxplot(self.all_scores, vert=True)
        plt.ylabel('Match Score')
        plt.title('Score Distribution (Box Plot)')
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()
        
        # Print statistics
        import statistics
        print("\n📈 Score Distribution Statistics:")
        print(f"  Total matches: {len(self.all_scores)}")
        print(f"  Mean: {statistics.mean(self.all_scores):.3f}")
        print(f"  Median: {statistics.median(self.all_scores):.3f}")
        print(f"  Std Dev: {statistics.stdev(self.all_scores) if len(self.all_scores) > 1 else 0:.3f}")
        print(f"  Min: {min(self.all_scores):.3f}")
        print(f"  Max: {max(self.all_scores):.3f}")


def process_csv_file(csv_path: str, mapper: CreativeMapper, mode: str = 'batch') -> pd.DataFrame:
    """
    Process entire CSV file and create output with creative mappings
    
    Args:
        csv_path: Path to source CSV file
        mapper: CreativeMapper instance
        mode: 'line-by-line' or 'batch'
    """
    # Read CSV
    df = pd.read_csv(csv_path)
    print(f"\n📄 Loaded CSV with {len(df)} rows")
    
    # Prepare output rows (will have multiple rows per CSV row if multiple dimensions)
    output_rows = []
    
    for idx, row in df.iterrows():
        creative_id = idx + 1  # 1-indexed creative_id
        
        # Convert row to dict for processing
        csv_row = row.to_dict()
        
        if mode == 'line-by-line':
            print(f"\n{'='*80}")
            print(f"Processing line {creative_id}/{len(df)}")
            print(f"{'='*80}")
        
        # Find matches
        matches = mapper.find_best_match(csv_row, top_n=10)
        
        if mode == 'line-by-line':
            mapper.print_match_results(csv_row, matches, show_grouped=True)
            input("\n⏸️  Press Enter to continue to next line...")
        
        # Get best scoring group
        if matches:
            grouped = mapper.group_by_dimension(matches)
            if grouped:
                # Get highest scoring group
                best_score = max(grouped.keys())
                best_variants = grouped[best_score]
                
                # Create one output row per dimension variant
                for variant in best_variants:
                    output_row = csv_row.copy()
                    output_row['creative_id'] = creative_id
                    output_row['match_score'] = variant['score']
                    output_row['dimension'] = variant['dimension']
                    output_row['filename'] = str(variant['file'])
                    output_rows.append(output_row)
            else:
                # No match found
                output_row = csv_row.copy()
                output_row['creative_id'] = creative_id
                output_row['match_score'] = 0.0
                output_row['dimension'] = None
                output_row['filename'] = None
                output_rows.append(output_row)
        else:
            # No match found
            output_row = csv_row.copy()
            output_row['creative_id'] = creative_id
            output_row['match_score'] = 0.0
            output_row['dimension'] = None
            output_row['filename'] = None
            output_rows.append(output_row)
    
    # Create output DataFrame
    output_df = pd.DataFrame(output_rows)
    
    # Reorder columns to put new columns after existing ones
    new_cols = ['creative_id', 'match_score', 'dimension', 'filename']
    other_cols = [col for col in output_df.columns if col not in new_cols]
    output_df = output_df[other_cols + new_cols]
    
    return output_df


def test_single_row():
    """Test with a single row from the CSV"""
    
    # Initialize mapper (save_output=False by default during development)
    base_path = os.path.dirname(os.path.abspath(__file__))
    mapper = CreativeMapper(base_path, save_output=False)
    
    # Build file cache
    mapper.build_file_cache()
    
    # Sample CSV row (first data row from the provided CSV)
    sample_row = {
        'real_ad_name': 'tim-con_perene_conversao_pedido_socialads_asc_cpm_nacional_facebook_gross_kv-custo-beneficio_27gb-38m_estatico',
        'Veículo': 'facebook',
        'Campanha': 'asc',
        'Segmentação': 'gross',
        'Oferta': '27gb-38m',
        'Criativo': 'kv-custo-beneficio',
        'Formato': 'estatico',
    }
    
    # Find matches
    print("\n🚀 Testing Creative Mapper with Sample Row")
    matches = mapper.find_best_match(sample_row, top_n=10)
    
    # Print results with grouping
    mapper.print_match_results(sample_row, matches, show_grouped=True)
    
    # Show score distribution
    mapper.plot_score_distribution()


def main():
    """Main interactive entry point"""
    print("\n" + "="*80)
    print("🎨 CREATIVE MAPPER - Ad Performance to Creative Files")
    print("="*80)
    
    # Initialize mapper
    base_path = os.path.dirname(os.path.abspath(__file__))
    mapper = CreativeMapper(base_path, save_output=False)
    
    # Build file cache
    mapper.build_file_cache()
    
    # Ask user for mode
    print("\n📋 Select Mode:")
    print("  1 - Line by line diagnosis (with detailed output for each line)")
    print("  2 - Batch process entire file")
    
    choice = input("\nEnter your choice (1 or 2): ")
    
    if choice == '1':
        mode = 'line-by-line'
        print("\n✅ Line-by-line mode selected")
    elif choice == '2':
        mode = 'batch'
        print("\n✅ Batch processing mode selected")
    else:
        print("\n❌ Invalid choice. Defaulting to batch mode.")
        mode = 'batch'
    
    # Get CSV path
    csv_path = input("\nEnter path to CSV file (or press Enter for default '../sourceadsdata.csv'): ").strip()
    if not csv_path:
        csv_path = os.path.join(os.path.dirname(base_path), 'sourceadsdata.csv')
    
    if not os.path.exists(csv_path):
        print(f"\n❌ CSV file not found: {csv_path}")
        return
    
    # Process CSV
    output_df = process_csv_file(csv_path, mapper, mode=mode)
    
    # Show results summary
    print("\n" + "="*80)
    print("📊 PROCESSING SUMMARY")
    print("="*80)
    print(f"  Total CSV rows: {output_df['creative_id'].nunique()}")
    print(f"  Total output rows (with dimension variants): {len(output_df)}")
    print(f"  Matched: {len(output_df[output_df['match_score'] > 0])}")
    print(f"  Unmatched: {len(output_df[output_df['match_score'] == 0])}")
    
    # Show score distribution
    print("\n📈 Showing score distribution...")
    mapper.plot_score_distribution()
    
    # Ask about saving
    if mapper.save_output:
        save_choice = 'y'
    else:
        save_choice = input("\n💾 Save output to CSV? (y/n): ").strip().lower()
    
    if save_choice == 'y':
        # Generate output filename
        csv_name = os.path.basename(csv_path)
        csv_base = os.path.splitext(csv_name)[0]
        output_path = os.path.join(os.path.dirname(csv_path), f"{csv_base}_creatives_mapped.csv")
        
        output_df.to_csv(output_path, index=False)
        print(f"\n✅ Output saved to: {output_path}")
    else:
        print("\n⏭️  Output not saved (as per save_output=False during development)")
    
    print("\n" + "="*80)
    print("✨ Done!")
    print("="*80)


if __name__ == "__main__":
    # For testing, run test_single_row()
    # For production, run main()
    
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        test_single_row()
    else:
        main()
