#!/usr/bin/env python3
"""
Filter customer order files to orders containing No Scan products.

Reads barcodes from Shopify_Launch_No_Scans.csv (Variant Barcode column), then
filters a Sales_By_Customer_*.xlsx file from datasource/original-data/ to keep
orders (Ticket number) that contain at least one line item whose Product value
matches a No Scan barcode.

When an order matches, all line items for that order are included in the output.
The output file keeps the same layout as the original (date range rows,
column headers, then filtered data rows).

Usage:
  py filter_orders_by_no_scans.py --orders-file Sales_By_Customer_Beddington_Un.xlsx
  py filter_orders_by_no_scans.py --orders-file Sales_By_Customer_Beddington_Un.xlsx --dry-run
"""

import argparse
import logging
import re
import sys
import time
from pathlib import Path

import pandas as pd

NO_SCANS_FILE = Path("Shopify_Launch_No_Scans.csv")
ORIGINAL_DATA_DIR = Path("datasource/original-data")
OUTPUT_DIR = Path("filtered-orders-no-scans")
ORDERS_SKIPROWS = 2

logger = logging.getLogger(__name__)


def normalize_identifier(value) -> str | None:
    """Normalize barcode/SKU values for comparison."""
    if pd.isna(value):
        return None

    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None

    if text.endswith(".0"):
        text = text[:-2]

    try:
        return str(int(float(text)))
    except (ValueError, OverflowError):
        return text


def load_no_scan_barcodes(no_scans_path: Path) -> set[str]:
    """Load normalized Variant Barcode values from the No Scans CSV."""
    if not no_scans_path.is_file():
        raise FileNotFoundError(f"No Scans file not found: {no_scans_path}")

    last_error = None
    for encoding in ("utf-8", "latin-1", "cp1252"):
        try:
            df = pd.read_csv(
                no_scans_path,
                usecols=["Variant Barcode"],
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
            f"Could not decode {no_scans_path}: {last_error}",
        )

    if "Variant Barcode" not in df.columns:
        raise ValueError(f"'Variant Barcode' column not found in {no_scans_path}")

    barcodes = {
        normalized
        for normalized in (normalize_identifier(value) for value in df["Variant Barcode"])
        if normalized
    }

    if not barcodes:
        raise ValueError(f"No barcodes found in {no_scans_path}")

    logger.info("Loaded %s No Scan barcodes from %s", len(barcodes), no_scans_path.name)
    return barcodes


def resolve_orders_path(orders_file: str) -> Path:
    """Resolve and validate the input orders file path."""
    orders_path = ORIGINAL_DATA_DIR / orders_file

    if not orders_path.is_file():
        raise FileNotFoundError(f"Orders file not found: {orders_path}")

    if not re.match(r"^Sales_By_Customer_.+\.xlsx$", orders_file, re.IGNORECASE):
        raise ValueError(
            "Orders file must match Sales_By_Customer_<name>.xlsx "
            f"(got: {orders_file})"
        )

    return orders_path


def load_header_rows(orders_path: Path) -> pd.DataFrame:
    """Load the first two metadata rows from the original orders file."""
    return pd.read_excel(
        orders_path,
        header=None,
        nrows=ORDERS_SKIPROWS,
        engine="openpyxl",
    )


def load_orders_file(orders_path: Path) -> pd.DataFrame:
    """Load the customer orders file (data rows only, after metadata headers)."""
    file_size_mb = orders_path.stat().st_size / (1024 * 1024)
    logger.info("Loading orders file (%.1f MB)...", file_size_mb)

    orders_df = pd.read_excel(
        orders_path,
        skiprows=ORDERS_SKIPROWS,
        engine="openpyxl",
    )

    for column in ("Product", "Ticket number"):
        if column not in orders_df.columns:
            raise ValueError(f"'{column}' column not found in orders file")

    return orders_df


def save_filtered_orders_file(
    orders_path: Path,
    filtered_df: pd.DataFrame,
    output_path: Path,
) -> None:
    """Write filtered data while preserving the original file's header layout."""
    header_rows = load_header_rows(orders_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        header_rows.to_excel(writer, index=False, header=False, startrow=0)
        filtered_df.to_excel(writer, index=False, header=True, startrow=ORDERS_SKIPROWS)


def filter_orders_by_no_scans(
    orders_df: pd.DataFrame,
    no_scan_barcodes: set[str],
) -> tuple[pd.DataFrame, dict]:
    """Return all line items for orders that contain a No Scan product."""
    normalized_products = orders_df["Product"].map(normalize_identifier)
    line_item_match_mask = normalized_products.isin(no_scan_barcodes)
    matching_tickets = set(orders_df.loc[line_item_match_mask, "Ticket number"].unique())

    filtered_df = orders_df[orders_df["Ticket number"].isin(matching_tickets)].copy()

    stats = {
        "input_rows": len(orders_df),
        "input_orders": orders_df["Ticket number"].nunique(),
        "matching_line_items": int(line_item_match_mask.sum()),
        "matching_orders": len(matching_tickets),
        "output_rows": len(filtered_df),
    }
    return filtered_df, stats


def build_output_path(orders_path: Path, output_dir: Path) -> Path:
    """Build the default filtered output file path."""
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / f"{orders_path.stem}_no_scans_filtered.xlsx"


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Filter a customer orders file to orders containing at least one "
            "No Scan product (by Variant Barcode). All line items from matching "
            "orders are included."
        )
    )
    parser.add_argument(
        "--orders-file",
        required=True,
        help="Orders file in datasource/original-data/ (e.g. Sales_By_Customer_Beddington_Un.xlsx)",
    )
    parser.add_argument(
        "--no-scans-file",
        default=str(NO_SCANS_FILE),
        help=f"Path to No Scans CSV (default: {NO_SCANS_FILE})",
    )
    parser.add_argument(
        "--output",
        help="Optional output .xlsx path (default: filtered-orders-no-scans/<input>_no_scans_filtered.xlsx)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scan and report matches without writing an output file",
    )
    return parser.parse_args()


def setup_logging() -> None:
    Path("logs").mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("logs/filter_orders_by_no_scans.log"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def main() -> int:
    setup_logging()
    args = parse_arguments()
    start_time = time.time()

    project_root = Path(__file__).resolve().parent
    if Path.cwd().resolve() != project_root:
        import os

        os.chdir(project_root)
        logger.info("Changed working directory to: %s", project_root)

    try:
        orders_path = resolve_orders_path(args.orders_file)
        no_scan_barcodes = load_no_scan_barcodes(Path(args.no_scans_file))

        logger.info("=" * 60)
        logger.info("Filtering orders by No Scan barcodes")
        logger.info("Orders file: %s", orders_path.name)
        logger.info("=" * 60)

        orders_df = load_orders_file(orders_path)
        filtered_df, stats = filter_orders_by_no_scans(orders_df, no_scan_barcodes)

        logger.info("Input rows:              %s", f"{stats['input_rows']:,}")
        logger.info("Input unique orders:     %s", f"{stats['input_orders']:,}")
        logger.info("Matching line items:     %s", f"{stats['matching_line_items']:,}")
        logger.info("Matching orders:         %s", f"{stats['matching_orders']:,}")

        if stats["matching_orders"] == 0:
            logger.info("No orders contain No Scan products. Nothing to export.")
            return 0

        if args.dry_run:
            logger.info(
                "Dry run complete — would export %s rows across %s orders.",
                f"{stats['output_rows']:,}",
                f"{stats['matching_orders']:,}",
            )
            return 0

        output_path = Path(args.output) if args.output else build_output_path(
            orders_path,
            OUTPUT_DIR,
        )
        save_filtered_orders_file(orders_path, filtered_df, output_path)

        elapsed = time.time() - start_time
        logger.info("Output rows:             %s", f"{stats['output_rows']:,}")
        logger.info("Output orders:           %s", f"{stats['matching_orders']:,}")
        logger.info("Saved to:                %s", output_path)
        logger.info("Completed in %.1f seconds", elapsed)
        return 0

    except (FileNotFoundError, ValueError) as exc:
        logger.error("%s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
