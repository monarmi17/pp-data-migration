#!/usr/bin/env python3
"""
Orders and Products Data Merger

This script merges the orders.xlsx and products.xlsx files to add Product Code
information to the orders data. The merge is performed using the SKU field
as the foreign key.

Author: AI Assistant
Date: 2024
"""

import pandas as pd
import os
import sys
from pathlib import Path


def load_data():
    """Load orders and products data from Excel files."""
    try:
        # Load orders data
        orders_path = Path("datasource/orders.xlsx")
        if not orders_path.exists():
            raise FileNotFoundError(f"Orders file not found: {orders_path}")
        
        orders_df = pd.read_excel(orders_path)
        print(f"Loaded orders data: {len(orders_df)} records")
        
        # Load products data
        products_path = Path("datasource/products.xlsx")
        if not products_path.exists():
            raise FileNotFoundError(f"Products file not found: {products_path}")
        
        products_df = pd.read_excel(products_path)
        print(f"Loaded products data: {len(products_df)} records")
        
        return orders_df, products_df
    
    except Exception as e:
        print(f"Error loading data: {e}")
        sys.exit(1)


def merge_data(orders_df, products_df):
    """
    Merge orders and products data to add Product Code information.
    
    Args:
        orders_df: DataFrame containing orders data
        products_df: DataFrame containing products data
    
    Returns:
        DataFrame with merged data
    """
    try:
        # Display column information for debugging
        print("\nOrders columns:", list(orders_df.columns))
        print("Products columns:", list(products_df.columns))
        
        # Check if required columns exist
        if 'Product' not in orders_df.columns:
            raise ValueError("'Product' column not found in orders data")
        
        if 'SKU' not in products_df.columns:
            raise ValueError("'SKU' column not found in products data")
        
        if 'Product Code' not in products_df.columns:
            raise ValueError("'Product Code' column not found in products data")
        
        # Create a mapping dictionary from products data
        # Use SKU as key and Product Code as value
        sku_to_product_code = products_df.set_index('SKU')['Product Code'].to_dict()
        print(f"\nCreated SKU to Product Code mapping: {len(sku_to_product_code)} entries")
        
        # Add Product Code column to orders data
        # Map Product column (SKU) to Product Code using the mapping
        orders_df['Product Code'] = orders_df['Product'].map(sku_to_product_code)
        
        # Check for any unmapped SKUs
        unmapped_skus = orders_df[orders_df['Product Code'].isna()]['Product'].unique()
        if len(unmapped_skus) > 0:
            print(f"\nWarning: {len(unmapped_skus)} SKUs could not be mapped to Product Code:")
            for sku in unmapped_skus:
                print(f"  - {sku}")
        
        # Reorder columns to place Product Code right after Product
        columns = list(orders_df.columns)
        product_index = columns.index('Product')
        
        # Remove Product Code from its current position and insert after Product
        columns.remove('Product Code')
        columns.insert(product_index + 1, 'Product Code')
        
        # Reorder the DataFrame
        merged_df = orders_df[columns]
        
        print(f"\nMerged data: {len(merged_df)} records")
        print(f"Successfully mapped: {merged_df['Product Code'].notna().sum()} records")
        
        return merged_df
    
    except Exception as e:
        print(f"Error merging data: {e}")
        sys.exit(1)


def save_data(merged_df):
    """Save the merged data to processed/orders.xlsx."""
    try:
        # Create processed directory if it doesn't exist
        processed_dir = Path("processed")
        processed_dir.mkdir(exist_ok=True)
        
        # Save to Excel file
        output_path = processed_dir / "orders.xlsx"
        merged_df.to_excel(output_path, index=False)
        
        print(f"\nData saved successfully to: {output_path}")
        print(f"File contains {len(merged_df)} records with {len(merged_df.columns)} columns")
        
        # Display sample of the merged data
        print("\nSample of merged data:")
        print(merged_df[['Product', 'Product Code', 'Product name', 'Product quantity']].head())
        
    except Exception as e:
        print(f"Error saving data: {e}")
        sys.exit(1)


def main():
    """Main function to orchestrate the data merging process."""
    print("Starting Orders and Products Data Merger")
    print("=" * 50)
    
    # Load data
    orders_df, products_df = load_data()
    
    # Merge data
    merged_df = merge_data(orders_df, products_df)
    
    # Save merged data
    save_data(merged_df)
    
    print("\nData merging completed successfully!")
    print("=" * 50)


if __name__ == "__main__":
    main()
