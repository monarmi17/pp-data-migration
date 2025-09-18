#!/usr/bin/env python3
"""
Import Error Analysis Script

Analyzes failed imports from orders.csv and products.csv files in the import-results directory.
Groups errors by generic error types and outputs summary CSV files for analysis.

Usage:
    python analyze_import_errors.py [--output-dir OUTPUT_DIR] [--verbose]

Output:
    - error-analysis/ directory (added to .gitignore)
    - Summary CSV files with error groupings and key identifiers
"""

import pandas as pd
import re
import os
import argparse
from datetime import datetime
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Any


class ImportErrorAnalyzer:
    """Analyzes import errors and groups them by generic error types."""
    
    def __init__(self, import_results_dir: str = "import-results", output_dir: str = "error-analysis"):
        self.import_results_dir = import_results_dir
        self.output_dir = output_dir
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Error pattern definitions
        self.error_patterns = {
            # Orders error patterns
            'duplicate_sku_variants': {
                'pattern': r'Found \[(\d+)\] Variants with the same SKU \[([^\]]+)\]',
                'description': 'Duplicate SKU variants found',
                'file_type': 'orders'
            },
            'missing_line_item_fields': {
                'pattern': r'Line Items: Name can\'t be blank, Title can\'t be blank',
                'description': 'Missing required line item fields (Name/Title)',
                'file_type': 'orders'
            },
            'invalid_line_items': {
                'pattern': r'Order: Line items is invalid',
                'description': 'Invalid line items structure',
                'file_type': 'orders'
            },
            
            # Products error patterns
            'inconsistent_title': {
                'pattern': r'"Title" differs in each row',
                'description': 'Inconsistent product titles across variants',
                'file_type': 'products'
            },
            'inconsistent_body_html': {
                'pattern': r'"Body HTML" differs in each row',
                'description': 'Inconsistent product descriptions across variants',
                'file_type': 'products'
            },
            'missing_required_fields': {
                'pattern': r'can\'t be blank',
                'description': 'Missing required product fields',
                'file_type': 'products'
            },
            
            # Generic patterns
            'validation_error': {
                'pattern': r'validation|invalid|error',
                'description': 'General validation errors',
                'file_type': 'both'
            },
            'duplicate_identifier': {
                'pattern': r'duplicate|already exists|taken',
                'description': 'Duplicate identifiers',
                'file_type': 'both'
            }
        }
    
    def load_failed_records(self, file_path: str) -> pd.DataFrame:
        """Load only failed records from a CSV file."""
        try:
            df = pd.read_csv(file_path)
            failed_df = df[df['Import Result'] == 'Failed'].copy()
            print(f"Loaded {len(failed_df)} failed records from {os.path.basename(file_path)}")
            return failed_df
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            return pd.DataFrame()
    
    def extract_error_details(self, comment: str) -> Dict[str, Any]:
        """Extract structured error details from import comment."""
        error_details = {
            'raw_comment': comment,
            'error_type': 'unknown',
            'error_description': 'Unknown error',
            'extracted_values': {}
        }
        
        # Check each error pattern
        for error_key, error_config in self.error_patterns.items():
            pattern = error_config['pattern']
            if re.search(pattern, comment, re.IGNORECASE):
                error_details['error_type'] = error_key
                error_details['error_description'] = error_config['description']
                
                # Extract specific values using regex groups
                match = re.search(pattern, comment, re.IGNORECASE)
                if match and match.groups():
                    error_details['extracted_values'] = {
                        f'group_{i+1}': group for i, group in enumerate(match.groups())
                    }
                break
        
        return error_details
    
    def get_key_identifiers(self, row: pd.Series, file_type: str) -> Dict[str, Any]:
        """Extract key identifiers for backtracking issues."""
        identifiers = {}
        
        if file_type == 'orders':
            identifiers.update({
                'order_name': row.get('Name', ''),
                'sku': row.get('Line: SKU', ''),
                'customer_email': row.get('Customer: Email', ''),
                'processed_at': row.get('Processed At', ''),
                'transaction_amount': row.get('Transaction: Amount', ''),
                'payment_status': row.get('Payment: Status', ''),
                'fulfillment_status': row.get('Fulfillment: Status', '')
            })
        elif file_type == 'products':
            identifiers.update({
                'handle': row.get('Handle', ''),
                'variant_sku': row.get('Variant SKU', ''),
                'title': row.get('Title', ''),
                'vendor': row.get('Vendor', ''),
                'status': row.get('Status', ''),
                'variant_price': row.get('Variant Price', ''),
                'cost_per_item': row.get('Cost per item', '')
            })
        
        return identifiers
    
    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze failed imports from a single file."""
        filename = os.path.basename(file_path)
        file_type = 'orders' if 'orders' in filename.lower() else 'products'
        
        print(f"\nAnalyzing {filename}...")
        
        # Load failed records
        failed_df = self.load_failed_records(file_path)
        if failed_df.empty:
            print(f"No failed records found in {filename}")
            return {}
        
        # Analyze each failed record
        analysis_results = []
        error_counts = Counter()
        
        for idx, row in failed_df.iterrows():
            # Extract error details
            error_details = self.extract_error_details(row['Import Comment'])
            
            # Get key identifiers
            identifiers = self.get_key_identifiers(row, file_type)
            
            # Create analysis record
            analysis_record = {
                'file_type': file_type,
                'row_index': idx,
                'error_type': error_details['error_type'],
                'error_description': error_details['error_description'],
                'raw_comment': error_details['raw_comment'],
                **identifiers,
                **error_details['extracted_values']
            }
            
            analysis_results.append(analysis_record)
            error_counts[error_details['error_type']] += 1
        
        # Create summary
        summary = {
            'file_type': file_type,
            'total_failed_records': len(failed_df),
            'error_counts': dict(error_counts),
            'analysis_results': analysis_results
        }
        
        print(f"Found {len(failed_df)} failed records with {len(error_counts)} error types")
        for error_type, count in error_counts.most_common():
            print(f"  - {error_type}: {count} records")
        
        return summary
    
    def create_summary_csv(self, all_analyses: List[Dict[str, Any]]) -> None:
        """Create summary CSV files for each file type."""
        
        for analysis in all_analyses:
            if not analysis:
                continue
                
            file_type = analysis['file_type']
            results_df = pd.DataFrame(analysis['analysis_results'])
            
            # Create summary filename (no timestamp)
            summary_filename = f"{file_type}_error_summary.csv"
            summary_path = os.path.join(self.output_dir, summary_filename)
            
            # Select only significant columns for analysis
            if file_type == 'orders':
                significant_columns = [
                    'error_type', 'error_description', 'order_name', 'sku', 
                    'customer_email', 'processed_at', 'transaction_amount',
                    'payment_status', 'fulfillment_status', 'raw_comment'
                ]
            else:  # products
                significant_columns = [
                    'error_type', 'error_description', 'handle', 'variant_sku',
                    'title', 'vendor', 'status', 'variant_price', 'cost_per_item',
                    'raw_comment'
                ]
            
            # Filter to available columns
            available_columns = [col for col in significant_columns if col in results_df.columns]
            summary_df = results_df[available_columns].copy()
            
            # Sort by error type for better analysis
            summary_df = summary_df.sort_values(['error_type', 'error_description'])
            
            # Save summary
            summary_df.to_csv(summary_path, index=False)
            print(f"Created summary: {summary_path}")
    
    def create_error_type_summary(self, all_analyses: List[Dict[str, Any]]) -> None:
        """Create a high-level error type summary."""
        
        # Combine all error counts
        total_error_counts = Counter()
        file_type_counts = defaultdict(Counter)
        
        for analysis in all_analyses:
            if not analysis:
                continue
                
            file_type = analysis['file_type']
            error_counts = analysis['error_counts']
            
            for error_type, count in error_counts.items():
                total_error_counts[error_type] += count
                file_type_counts[file_type][error_type] += count
        
        # Create summary DataFrame
        summary_data = []
        for error_type, total_count in total_error_counts.most_common():
            summary_data.append({
                'error_type': error_type,
                'total_count': total_count,
                'orders_count': file_type_counts['orders'].get(error_type, 0),
                'products_count': file_type_counts['products'].get(error_type, 0),
                'description': self.error_patterns.get(error_type, {}).get('description', 'Unknown error')
            })
        
        summary_df = pd.DataFrame(summary_data)
        
        # Save error type summary (no timestamp)
        summary_filename = "error_type_summary.csv"
        summary_path = os.path.join(self.output_dir, summary_filename)
        summary_df.to_csv(summary_path, index=False)
        print(f"Created error type summary: {summary_path}")
        
        # Print summary to console
        print(f"\n{'='*60}")
        print("ERROR ANALYSIS SUMMARY")
        print(f"{'='*60}")
        print(f"Total failed records analyzed: {sum(total_error_counts.values())}")
        print(f"Unique error types found: {len(total_error_counts)}")
        print(f"\nTop error types:")
        for _, row in summary_df.head(10).iterrows():
            print(f"  {row['error_type']}: {row['total_count']} records ({row['description']})")
    
    def run_analysis(self) -> None:
        """Run the complete error analysis."""
        print("Starting Import Error Analysis...")
        print(f"Import results directory: {self.import_results_dir}")
        print(f"Output directory: {self.output_dir}")
        
        # Find CSV files in import-results directory
        csv_files = []
        if os.path.exists(self.import_results_dir):
            for file in os.listdir(self.import_results_dir):
                if file.endswith('.csv'):
                    csv_files.append(os.path.join(self.import_results_dir, file))
        
        if not csv_files:
            print(f"No CSV files found in {self.import_results_dir}")
            return
        
        print(f"Found CSV files: {[os.path.basename(f) for f in csv_files]}")
        
        # Analyze each file
        all_analyses = []
        for csv_file in csv_files:
            analysis = self.analyze_file(csv_file)
            all_analyses.append(analysis)
        
        # Create summary files
        self.create_summary_csv(all_analyses)
        self.create_error_type_summary(all_analyses)
        
        print(f"\nAnalysis complete! Results saved to: {self.output_dir}")


def main():
    """Main function with command line argument parsing."""
    parser = argparse.ArgumentParser(
        description="Analyze failed imports from CSV files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python analyze_import_errors.py
    python analyze_import_errors.py --output-dir custom-analysis
    python analyze_import_errors.py --verbose
        """
    )
    
    parser.add_argument(
        '--output-dir',
        default='error-analysis',
        help='Output directory for analysis results (default: error-analysis)'
    )
    
    parser.add_argument(
        '--import-results-dir',
        default='import-results',
        help='Directory containing import result CSV files (default: import-results)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    # Create analyzer and run analysis
    analyzer = ImportErrorAnalyzer(
        import_results_dir=args.import_results_dir,
        output_dir=args.output_dir
    )
    
    analyzer.run_analysis()


if __name__ == "__main__":
    main()
