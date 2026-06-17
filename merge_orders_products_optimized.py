#!/usr/bin/env python3
"""
Orders and Products Data Merger - Optimized for Large Datasets

This script merges the orders.xlsx and products.xlsx files to add Product Code
information to the orders data. Optimized for handling large datasets (500k+ orders).

Supports test mode and production mode:
- Test mode: Uses test-data/orders.xlsx and test-data/products.xlsx
- Production mode: Uses original-data/<region>_orders.xlsx and original-data/Products.csv

Key optimizations:
- Memory-efficient chunked processing
- Progress tracking and logging
- Optimized data types
- Efficient file I/O operations
- Region-specific file naming

Author: AI Assistant
Date: 2024
"""

import pandas as pd
import os
import sys
import time
import gc
import re
from pathlib import Path
from datetime import datetime
import logging
import argparse


# Configure logging (will be updated in main() based on mode)
logger = logging.getLogger(__name__)

# Configuration for large dataset processing
CHUNK_SIZE = 50000  # Process orders in chunks of 50k rows
PROGRESS_INTERVAL = 10000  # Show progress every 10k rows


def extract_region_from_filename(filename):
    """Extract region name from filename like Sales_By_Customer_Auburn_Bay.xlsx"""
    try:
        # Remove file extension
        name_without_ext = filename.replace('.xlsx', '').replace('.csv', '')

        # Pattern to match Sales_By_Customer_<region> format
        pattern = r'Sales_By_Customer_(.+)'
        match = re.search(pattern, name_without_ext, re.IGNORECASE)

        if match:
            region = match.group(1)
            # Convert to snake_case and lowercase
            region = region.replace(' ', '_').replace('-', '_').lower()
            return region

        # If no pattern match, try to extract last part after underscores
        parts = name_without_ext.split('_')
        if len(parts) > 1:
            return '_'.join(parts[-2:]).lower()  # Take last two parts

        return name_without_ext.lower()

    except Exception as e:
        logger.warning(f"Could not extract region from filename '{filename}': {e}")
        return "unknown_region"


# Configuration for large dataset processing
CHUNK_SIZE = 50000  # Process orders in chunks of 50k rows
PROGRESS_INTERVAL = 10000  # Show progress every 10k rows
DEFAULT_PRODUCTS_FILE = "Products.csv"
ORIGINAL_DATA_DIR = Path("datasource/original-data")


def validate_orders_filename(orders_file: str) -> None:
    """Reject Excel lock/temp files (~$...) mistaken for real order workbooks."""
    if orders_file.startswith("~$"):
        raise ValueError(
            f"'{orders_file}' is an Excel temporary lock file (created while the "
            "workbook is open), not the actual orders file. Close the file in "
            "Excel and pass the real filename, e.g. "
            "Sales_By_Customer_Aspen_May_reimport.xlsx"
        )


def normalize_barcode(value):
    """Normalize a barcode/SKU value for lookup (12-digit zero-padded when numeric)."""
    if pd.isna(value):
        return None

    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None

    if text.endswith(".0"):
        text = text[:-2]

    try:
        return str(int(float(text))).zfill(12)
    except (ValueError, OverflowError):
        return text


def barcode_lookup_key(variant_barcode):
    """Build lookup key from Variant Barcode; use only the part before '-' when present."""
    if pd.isna(variant_barcode):
        return None

    text = str(variant_barcode).strip()
    if not text or text.lower() == "nan":
        return None

    if "-" in text:
        text = text.split("-", 1)[0].strip()

    return normalize_barcode(text)


def normalize_order_product(value):
    """Normalize order line Product values for barcode lookup."""
    return normalize_barcode(value)


def apply_product_mapping(chunk_df, product_mapping):
    """Add Product Code and update Product with exact catalog barcode when matched."""
    chunk_df["Product_normalized"] = chunk_df["Product"].map(normalize_order_product)

    chunk_df["Product Code"] = chunk_df["Product_normalized"].map(
        lambda key: product_mapping[key]["product_code"]
        if key and key in product_mapping
        else None
    )

    def resolve_product(row):
        key = row["Product_normalized"]
        if key and key in product_mapping:
            exact_barcode = product_mapping[key].get("variant_barcode")
            if exact_barcode:
                return exact_barcode
        return row["Product"]

    chunk_df["Product"] = chunk_df.apply(resolve_product, axis=1)
    return chunk_df.drop(columns=["Product_normalized"])


def _add_mapping_entry(product_mapping, lookup_key, product_code, variant_barcode):
    """Insert or replace a barcode lookup entry."""
    if not lookup_key or pd.isna(product_code) or str(product_code).strip().lower() == "nan":
        return

    product_code = str(product_code).strip()
    variant_barcode = None if pd.isna(variant_barcode) else str(variant_barcode).strip()
    new_entry = {
        "product_code": product_code,
        "variant_barcode": variant_barcode,
    }

    existing = product_mapping.get(lookup_key)
    if existing is None:
        product_mapping[lookup_key] = new_entry
        return

    existing_has_dash = "-" in str(existing.get("variant_barcode") or "")
    new_has_dash = "-" in str(variant_barcode or "")
    if new_has_dash and not existing_has_dash:
        product_mapping[lookup_key] = new_entry


def load_products_from_csv(products_path):
    """Load Shopify Products.csv and build barcode -> SKU mapping."""
    last_error = None
    for encoding in ("utf-8", "latin-1", "cp1252"):
        try:
            products_df = pd.read_csv(
                products_path,
                usecols=["Variant Barcode", "Variant SKU"],
                dtype=str,
                encoding=encoding,
            )
            break
        except UnicodeDecodeError as exc:
            last_error = exc
    else:
        raise UnicodeDecodeError(
            "unknown",
            b"",
            0,
            1,
            f"Could not decode {products_path}: {last_error}",
        )

    for column in ("Variant Barcode", "Variant SKU"):
        if column not in products_df.columns:
            raise ValueError(f"'{column}' column not found in {products_path}")

    product_mapping = {}
    dash_entries = 0

    for _, row in products_df.iterrows():
        lookup_key = barcode_lookup_key(row["Variant Barcode"])
        if not lookup_key:
            continue

        if "-" in str(row["Variant Barcode"]):
            dash_entries += 1

        _add_mapping_entry(
            product_mapping,
            lookup_key,
            row["Variant SKU"],
            row["Variant Barcode"],
        )

    logger.info(
        "Created barcode mapping with %s entries (%s dash-prefixed barcodes)",
        f"{len(product_mapping):,}",
        f"{dash_entries:,}",
    )
    return product_mapping


def load_products_from_xlsx(products_path):
    """Load legacy products.xlsx and build barcode -> Product Code mapping."""
    products_df = pd.read_excel(
        products_path,
        usecols=["SKU", "Product Code"],
        engine="openpyxl",
    )

    for column in ("SKU", "Product Code"):
        if column not in products_df.columns:
            raise ValueError(f"'{column}' column not found in products data")

    products_df["SKU"] = products_df["SKU"].map(normalize_barcode)

    initial_count = len(products_df)
    products_df = products_df.drop_duplicates(subset=["SKU"], keep="first")
    if len(products_df) < initial_count:
        logger.warning(
            "Removed %s duplicate SKUs from products data",
            initial_count - len(products_df),
        )

    product_mapping = {
        row["SKU"]: {
            "product_code": str(row["Product Code"]).strip(),
            "variant_barcode": None,
        }
        for _, row in products_df.iterrows()
        if row["SKU"] and pd.notna(row["Product Code"])
    }

    logger.info("Created SKU mapping with %s entries", f"{len(product_mapping):,}")
    return product_mapping


def load_products_data(test_mode=False, products_file=None):
    """Load products reference and build barcode/SKU lookup mapping."""
    try:
        if test_mode:
            products_path = Path("datasource/test-data/products.xlsx")
        else:
            products_path = ORIGINAL_DATA_DIR / (products_file or DEFAULT_PRODUCTS_FILE)

        if not products_path.exists():
            raise FileNotFoundError(f"Products file not found: {products_path}")

        logger.info("Loading products data from %s...", products_path)
        start_time = time.time()

        if products_path.suffix.lower() == ".csv":
            product_mapping = load_products_from_csv(products_path)
        else:
            product_mapping = load_products_from_xlsx(products_path)

        load_time = time.time() - start_time
        logger.info("Loaded products reference in %.2f seconds", load_time)
        gc.collect()

        return product_mapping

    except Exception as e:
        logger.error(f"Error loading products data: {e}")
        sys.exit(1)


def get_orders_info(test_mode=False, orders_file=None, region_name=None, orders_dir=None):
    """Get basic information about orders file without loading all data."""
    try:
        if test_mode:
            orders_path = Path("datasource/test-data/orders.xlsx")
            skiprows = 0  # Test data has no extra header rows
        else:
            base_dir = Path(orders_dir or "datasource/original-data")
            if orders_file:
                validate_orders_filename(orders_file)
                orders_path = base_dir / orders_file
                skiprows = 2  # Original data has 2 extra header rows to skip
            elif region_name:
                # Construct filename from region name
                # Convert region_name like "auburn_bay" to "Auburn_Bay"
                formatted_region = '_'.join(word.capitalize() for word in region_name.split('_'))
                orders_filename = f"Sales_By_Customer_{formatted_region}.xlsx"
                orders_path = base_dir / orders_filename
                skiprows = 2  # Original data has 2 extra header rows to skip
            else:
                # Default fallback
                orders_path = base_dir / "orders.xlsx"
                skiprows = 2  # Original data has 2 extra header rows to skip

        if not orders_path.exists():
            raise FileNotFoundError(f"Orders file not found: {orders_path}")

        # Read just the first few rows to get column info and estimate size
        # Skip the first 2 rows for original data, 0 rows for test data
        sample_df = pd.read_excel(orders_path, nrows=100, skiprows=skiprows, engine='openpyxl')

        # Get total row count efficiently
        logger.info(f"Analyzing orders file structure: {orders_path}...")
        if skiprows > 0:
            logger.info(f"Skipping first {skiprows} header rows for original data")

        # Check for required columns
        if 'Product' not in sample_df.columns:
            raise ValueError("'Product' column not found in orders data")

        return orders_path, sample_df.columns.tolist(), skiprows

    except Exception as e:
        logger.error(f"Error analyzing orders file: {e}")
        sys.exit(1)


def process_orders_chunk(chunk_df, product_mapping, chunk_num, total_chunks):
    """Process a single chunk of orders data."""
    try:
        chunk_df = apply_product_mapping(chunk_df, product_mapping)

        # Count successful mappings in this chunk
        mapped_count = chunk_df['Product Code'].notna().sum()
        unmapped_count = len(chunk_df) - mapped_count

        if unmapped_count > 0:
            unmapped_skus = chunk_df[chunk_df['Product Code'].isna()]['Product'].unique()
            logger.warning(f"Chunk {chunk_num}/{total_chunks}: {unmapped_count} unmapped SKUs found")
            # Log first few unmapped SKUs for debugging
            if len(unmapped_skus) <= 5:
                logger.warning(f"Unmapped SKUs: {list(unmapped_skus)}")
            else:
                logger.warning(f"First 5 unmapped SKUs: {list(unmapped_skus[:5])}")

        logger.info(f"Chunk {chunk_num}/{total_chunks}: Processed {len(chunk_df):,} records, "
                   f"{mapped_count:,} mapped, {unmapped_count:,} unmapped")

        return chunk_df, mapped_count, unmapped_count

    except Exception as e:
        logger.error(f"Error processing chunk {chunk_num}: {e}")
        raise


def reorder_columns(df):
    """Reorder columns to place Product Code right after Product."""
    columns = list(df.columns)
    if 'Product Code' in columns and 'Product' in columns:
        product_index = columns.index('Product')
        columns.remove('Product Code')
        columns.insert(product_index + 1, 'Product Code')
        return df[columns]
    return df


def save_error_rows(error_rows_list, region_name, step_name):
    """Save error/ignored rows to a separate file for manual review."""
    try:
        if not error_rows_list:
            return

        # Create error-rows directory
        error_dir = Path("error-rows")
        error_dir.mkdir(exist_ok=True)

        # Combine all error rows
        all_error_rows = pd.concat(error_rows_list, ignore_index=True)

        # Create timestamped filename following naming convention
        timestamp = datetime.now().strftime("%Y_%m_%d_%H%M%S")
        error_filename = f"{region_name}_{step_name}_error_rows_{timestamp}.csv"
        error_path = error_dir / error_filename

        # Save error rows to CSV file
        all_error_rows.to_csv(error_path, index=False)

        logger.info(f"Saved {len(all_error_rows):,} error/ignored rows to: {error_path}")

    except Exception as e:
        logger.warning(f"Could not save error rows: {e}")


def merge_data_simple(orders_path, columns, product_mapping, region_name="test", skiprows=0):
    """
    Simple merge for small datasets - loads entire file into memory.
    """
    try:
        logger.info("Loading orders data for simple processing...")
        start_time = time.time()

        # Load entire orders file with proper skiprows
        orders_df = pd.read_excel(orders_path, skiprows=skiprows, engine='openpyxl')

        # Track error/ignored rows
        error_rows = []

        orders_df = apply_product_mapping(orders_df, product_mapping)

        # Identify rows with missing Product Code (unmapped SKUs)
        unmapped_mask = orders_df['Product Code'].isna()
        if unmapped_mask.any():
            unmapped_rows = orders_df[unmapped_mask].copy()
            unmapped_rows['Error_Reason'] = 'Product SKU not found in products database'
            error_rows.append(unmapped_rows)

        # Count mappings
        total_mapped = orders_df['Product Code'].notna().sum()
        total_unmapped = len(orders_df) - total_mapped

        if total_unmapped > 0:
            unmapped_skus = orders_df[orders_df['Product Code'].isna()]['Product'].unique()
            logger.warning(f"{total_unmapped} unmapped SKUs found")
            if len(unmapped_skus) <= 10:
                logger.warning(f"Unmapped SKUs: {list(unmapped_skus)}")
            else:
                logger.warning(f"First 10 unmapped SKUs: {list(unmapped_skus[:10])}")

        # Save error/ignored rows if any
        if error_rows:
            save_error_rows(error_rows, region_name, "merge")

        # Reorder columns
        orders_df = reorder_columns(orders_df)

        # Create processed directory
        processed_dir = Path("order-line-items-with-product-codes")
        processed_dir.mkdir(exist_ok=True)

        # Split mapped vs unmapped
        mapped_df = orders_df[orders_df['Product Code'].notna()].copy()
        unmapped_df = orders_df[orders_df['Product Code'].isna()].copy()

        # Keep important columns first
        important_cols = [col for col in ['Product', 'Product Name', 'Product Code', 'Error_Reason'] if col in unmapped_df.columns]
        unmapped_df = unmapped_df[important_cols + [c for c in unmapped_df.columns if c not in important_cols]]

        # Create filenames
        mapped_filename = f"{region_name}_mapped_order_line_items_with_product_codes.xlsx"
        unmapped_filename = f"{region_name}_unmapped_order_line_items_with_product_codes.xlsx"

        mapped_path = processed_dir / mapped_filename
        unmapped_path = processed_dir / unmapped_filename

        # Save to Excel files
        mapped_df.to_excel(mapped_path, index=False, engine='openpyxl')
        unmapped_df.to_excel(unmapped_path, index=False, engine='openpyxl')

        # Also save full combined file for validation
        combined_filename = f"{region_name}_order_line_items_with_product_codes.xlsx"
        combined_path = processed_dir / combined_filename
        orders_df.to_excel(combined_path, index=False, engine='openpyxl')
        logger.info(f"Saved combined file to: {combined_path}")

        logger.info(f"Output files:")
        logger.info(f"  - {mapped_path} ({len(mapped_df):,} rows)")
        logger.info(f"  - {unmapped_path} ({len(unmapped_df):,} rows)")
        logger.info(f"  - {combined_path} ({len(orders_df):,} rows)")

        processing_time = time.time() - start_time

        logger.info(f"\n{'='*60}")
        logger.info(f"Simple processing completed successfully!")
        logger.info(f"Total records processed: {len(orders_df):,}")
        logger.info(f"Successfully mapped: {total_mapped:,} ({total_mapped/len(orders_df)*100:.1f}%)")
        logger.info(f"Unmapped records: {total_unmapped:,} ({total_unmapped/len(orders_df)*100:.1f}%)")
        logger.info(f"Processing time: {processing_time:.2f} seconds")
        logger.info(f"Output file: {mapped_path}")
        logger.info(f"Output file: {unmapped_path}")
        logger.info(f"{'='*60}")

        return len(orders_df), total_mapped, total_unmapped

    except Exception as e:
        logger.error(f"Error in simple processing: {e}")
        sys.exit(1)


def merge_data_chunked(orders_path, columns, product_mapping, region_name="test", skiprows=0):
    """
    Merge orders and products data using chunked processing for memory efficiency.
    Since pd.read_excel doesn't support chunksize, we'll convert to CSV first and then process in chunks.
    """
    try:
        logger.info(f"Starting chunked processing with chunk size: {CHUNK_SIZE:,}")
        logger.info("Note: Converting Excel to CSV first for chunked processing...")

        # Create temporary CSV file for chunked processing in a writable directory
        import tempfile
        temp_csv_path = Path(tempfile.gettempdir()) / "temp_orders.csv"

        # Convert Excel to CSV first
        logger.info("Converting Excel file to CSV for chunked processing...")
        conversion_start = time.time()

        # Read Excel file with proper skiprows and save as CSV
        orders_df_full = pd.read_excel(orders_path, skiprows=skiprows, engine='openpyxl')
        orders_df_full.to_csv(temp_csv_path, index=False)
        total_records = len(orders_df_full)

        # Clean up the full dataframe to free memory
        del orders_df_full
        gc.collect()

        conversion_time = time.time() - conversion_start
        logger.info(f"Conversion completed in {conversion_time:.2f} seconds. Total records: {total_records:,}")

        # Initialize counters and error tracking
        total_processed = 0
        total_mapped = 0
        total_unmapped = 0
        chunk_num = 0
        all_error_rows = []

        # Create processed directory
        processed_dir = Path("order-line-items-with-product-codes")
        processed_dir.mkdir(exist_ok=True)

        # Create region-specific output filename
        output_filename = f"{region_name}_order_line_items_with_product_codes.xlsx"
        output_path = processed_dir / output_filename

        # Initialize list to store processed chunks
        processed_chunks = []

        start_time = time.time()

        # Calculate total chunks
        total_chunks = (total_records + CHUNK_SIZE - 1) // CHUNK_SIZE
        logger.info(f"Will process {total_chunks} chunks of up to {CHUNK_SIZE:,} records each")

        # Process CSV file in chunks
        for chunk_df in pd.read_csv(temp_csv_path, chunksize=CHUNK_SIZE):
            chunk_num += 1

            # Process the chunk
            processed_chunk, mapped_count, unmapped_count = process_orders_chunk(
                chunk_df, product_mapping, chunk_num, total_chunks
            )

            # Track error rows for this chunk
            unmapped_mask = processed_chunk['Product Code'].isna()
            if unmapped_mask.any():
                chunk_error_rows = processed_chunk[unmapped_mask].copy()
                chunk_error_rows['Error_Reason'] = 'Product SKU not found in products database'
                chunk_error_rows['Chunk_Number'] = chunk_num
                all_error_rows.append(chunk_error_rows)

            # Reorder columns
            processed_chunk = reorder_columns(processed_chunk)

            # Store processed chunk
            processed_chunks.append(processed_chunk)

            # Update counters
            total_processed += len(processed_chunk)
            total_mapped += mapped_count
            total_unmapped += unmapped_count

            # Log progress
            elapsed_time = time.time() - start_time
            if total_processed % PROGRESS_INTERVAL == 0 or total_processed < PROGRESS_INTERVAL:
                rate = total_processed / elapsed_time if elapsed_time > 0 else 0
                logger.info(f"Progress: {total_processed:,} records processed "
                           f"({rate:.0f} records/sec)")

            # Clean up chunk to free memory
            del chunk_df, processed_chunk
            gc.collect()

        # Save error rows if any
        if all_error_rows:
            save_error_rows(all_error_rows, region_name, "merge")

        # Clean up temporary CSV file
        if temp_csv_path.exists():
            temp_csv_path.unlink()
            logger.info("Cleaned up temporary CSV file")

        # Combine all processed chunks and save to Excel
        logger.info("Combining processed chunks and splitting mapped/unmapped...")

        if len(processed_chunks) == 1:
            final_df = processed_chunks[0]
        else:
            final_df = pd.concat(processed_chunks, ignore_index=True)

        # Split mapped vs unmapped
        mapped_df = final_df[final_df['Product Code'].notna()].copy()
        unmapped_df = final_df[final_df['Product Code'].isna()].copy()

        # Keep important columns first
        important_cols = [col for col in ['Product', 'Product Name', 'Product Code', 'Error_Reason'] if col in unmapped_df.columns]
        unmapped_df = unmapped_df[important_cols + [c for c in unmapped_df.columns if c not in important_cols]]

        # Create filenames
        mapped_filename = f"{region_name}_mapped_order_line_items_with_product_codes.xlsx"
        unmapped_filename = f"{region_name}_unmapped_order_line_items_with_product_codes.xlsx"

        mapped_path = processed_dir / mapped_filename
        unmapped_path = processed_dir / unmapped_filename

        # Save both
        mapped_df.to_excel(mapped_path, index=False, engine='openpyxl')
        unmapped_df.to_excel(unmapped_path, index=False, engine='openpyxl')

        logger.info(f"Output files:")
        logger.info(f"  - {mapped_path} ({len(mapped_df):,} rows)")
        logger.info(f"  - {unmapped_path} ({len(unmapped_df):,} rows)")

        # Save to Excel file with explicit engine specification
        try:
            final_df.to_excel(output_path, index=False, engine='openpyxl')
            logger.info(f"Successfully saved {len(final_df):,} records to Excel file")
        except Exception as excel_error:
            logger.warning(f"Excel save failed with openpyxl: {excel_error}")
            logger.info("Trying alternative save method...")
            # Fallback to xlsxwriter if available
            try:
                final_df.to_excel(output_path, index=False, engine='xlsxwriter')
                logger.info(f"Successfully saved {len(final_df):,} records using xlsxwriter")
            except Exception as fallback_error:
                logger.error(f"All Excel save methods failed: {fallback_error}")
                # Save as CSV as last resort
                csv_path = output_path.with_suffix('.csv')
                final_df.to_csv(csv_path, index=False)
                logger.info(f"Saved as CSV instead: {csv_path}")
                output_path = csv_path

        # Clean up
        del processed_chunks, final_df
        gc.collect()

        processing_time = time.time() - start_time
        total_time_with_conversion = processing_time + conversion_time

        logger.info(f"\n{'='*60}")
        logger.info(f"Processing completed successfully!")
        logger.info(f"Total records processed: {total_processed:,}")
        logger.info(f"Successfully mapped: {total_mapped:,} ({total_mapped/total_processed*100:.1f}%)")
        logger.info(f"Unmapped records: {total_unmapped:,} ({total_unmapped/total_processed*100:.1f}%)")
        logger.info(f"Processing time (excl. conversion): {processing_time:.2f} seconds")
        logger.info(f"Total time (incl. conversion): {total_time_with_conversion:.2f} seconds")
        logger.info(f"Processing rate: {total_processed/processing_time:.0f} records/second")
        logger.info(f"Output file: {output_path}")
        logger.info(f"{'='*60}")

        return total_processed, total_mapped, total_unmapped

    except Exception as e:
        logger.error(f"Error in chunked processing: {e}")
        # Clean up temporary file on error
        import tempfile
        temp_csv_path = Path(tempfile.gettempdir()) / "temp_orders.csv"
        if temp_csv_path.exists():
            temp_csv_path.unlink()
        sys.exit(1)


def validate_output(output_path, expected_records):
    """Validate the output file."""
    try:
        logger.info("Validating output file...")

        # Quick validation by reading just the first few rows
        sample_df = pd.read_excel(output_path, nrows=10, engine='openpyxl')

        logger.info(f"Output file columns: {list(sample_df.columns)}")
        logger.info("Sample of merged data:")

        # Show sample with relevant columns
        display_cols = ['Product', 'Product Code']
        if 'Product name' in sample_df.columns:
            display_cols.append('Product name')
        if 'Product quantity' in sample_df.columns:
            display_cols.append('Product quantity')

        available_cols = [col for col in display_cols if col in sample_df.columns]
        if available_cols:
            logger.info(f"\n{sample_df[available_cols].head()}")

        # Get file size
        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info(f"Output file size: {file_size_mb:.1f} MB")

    except Exception as e:
        logger.warning(f"Could not validate output file: {e}")


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Merge orders and products data with region-specific naming')
    parser.add_argument('--test', action='store_true', help='Run in test mode using test data')
    parser.add_argument('--orders-file', type=str, help='Specific orders file to process (for production mode)')
    parser.add_argument('--orders-dir', type=str, default='datasource/original-data',
                        help='Directory containing the orders file (default: datasource/original-data)')
    parser.add_argument('--products-file', type=str, default=DEFAULT_PRODUCTS_FILE,
                        help=f'Products reference file in datasource/original-data/ (default: {DEFAULT_PRODUCTS_FILE})')
    parser.add_argument('--region', type=str, help='Region name to use for output files (overrides auto-detection)')
    return parser.parse_args()


def setup_logging(test_mode=False, region_name="test"):
    """Setup logging configuration based on mode."""
    log_filename = f"logs/data_merger_{region_name}.log" if not test_mode else "logs/data_merger_test.log"

    # Ensure logs directory exists
    Path("logs").mkdir(exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler(sys.stdout)
        ]
    )


def main():
    """Main function to orchestrate the data merging process."""
    start_time = time.time()

    # Parse arguments
    args = parse_arguments()

    # Determine region name
    region_name = "test"
    if not args.test:
        if args.region:
            region_name = args.region
        elif args.orders_file:
            region_name = extract_region_from_filename(args.orders_file)
        else:
            logger.error("For production mode, either --orders-file or --region must be specified")
            sys.exit(1)

    # Setup logging
    setup_logging(args.test, region_name)

    logger.info("="*60)
    logger.info("Starting Orders and Products Data Merger (Optimized)")
    if args.test:
        logger.info("Running in TEST MODE")
    else:
        logger.info(f"Running in PRODUCTION MODE - Region: {region_name}")
    logger.info("="*60)

    # Load products data and create mapping
    product_mapping = load_products_data(args.test, args.products_file)

    # Get orders file information
    orders_path, columns, skiprows = get_orders_info(
        args.test, args.orders_file, region_name, args.orders_dir
    )

    # Check file size to determine processing method
    file_size_mb = orders_path.stat().st_size / (1024 * 1024)
    logger.info(f"Orders file size: {file_size_mb:.1f} MB")

    if file_size_mb < 10:  # Small file - use simple approach
        logger.info("Small dataset detected - using simple processing method")
        total_processed, total_mapped, total_unmapped = merge_data_simple(
            orders_path, columns, product_mapping, region_name, skiprows
        )
    else:  # Large file - use chunked processing
        logger.info("Large dataset detected - using chunked processing method")
        total_processed, total_mapped, total_unmapped = merge_data_chunked(
            orders_path, columns, product_mapping, region_name, skiprows
        )

    # Validate output
    output_filename = f"{region_name}_order_line_items_with_product_codes.xlsx"
    output_path = Path("order-line-items-with-product-codes") / output_filename
    if not output_path.exists():
        # Try CSV fallback
        csv_filename = f"{region_name}_order_line_items_with_product_codes.csv"
        output_path = Path("order-line-items-with-product-codes") / csv_filename

    validate_output(output_path, total_processed)

    # Final summary
    total_time = time.time() - start_time
    logger.info(f"\nTotal execution time: {total_time:.2f} seconds")
    logger.info("Data merging completed successfully!")
    logger.info("="*60)


if __name__ == "__main__":
    main()
