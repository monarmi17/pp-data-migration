#!/usr/bin/env python3
"""
split_shopify_orders_by_location.py

Reads raw Shopify order export CSV(s) and splits them into per-location files:
  orders_export_{location}_Shopify_May.csv

Location is taken from the Location column (forward-filled per order). If empty,
falls back to Tags value "fulfilled-by: <location>".

Usage:
  py split_shopify_orders_by_location.py
  py split_shopify_orders_by_location.py --input-dir shopify-orders/raw
  py split_shopify_orders_by_location.py --period Shopify_May --dry-run
"""

import argparse
import logging
import re
import sys
from pathlib import Path

import pandas as pd

DEFAULT_INPUT_DIR = Path("shopify-orders/raw")
DEFAULT_OUTPUT_DIR = Path("shopify-orders")
DEFAULT_PERIOD = "Shopify_May"
NO_LOCATION_SLUG = "no_location"
OUTPUT_PATTERN = re.compile(r"^orders_export_.+_Shopify_.+\.csv$", re.IGNORECASE)
NO_LOCATION_OUTPUT_PATTERN = re.compile(
    r"^orders_export_(no_location|no-location)_Shopify_.+\.csv$", re.IGNORECASE
)

# Second word treated as location suffix -> use first word only (Aspen Landing -> Aspen)
LOCATION_SUFFIX_WORDS = frozenset({
    "landing", "station", "square", "heights", "market", "ridge", "woods",
    "village", "centre", "center", "plaza", "mall", "park", "gate", "gates",
    "hills", "hill", "west", "east", "north", "south", "commons", "crossing",
})

logger = logging.getLogger(__name__)


def location_to_slug(location: str) -> str:
    """Convert Shopify location name to filename slug (e.g. Aspen Landing -> Aspen)."""
    text = re.sub(r"\s+", " ", location.strip())
    parts = text.split(" ")
    if len(parts) == 2 and parts[1].lower() in LOCATION_SUFFIX_WORDS:
        return parts[0]
    slug = re.sub(r"[^\w]+", "_", text)
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug


def read_csv(path: Path) -> pd.DataFrame:
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            return pd.read_csv(path, dtype=str, encoding=enc, low_memory=False)
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"Cannot decode {path}")


def resolve_location(row: pd.Series) -> str | None:
    loc = row.get("Location")
    if pd.notna(loc) and str(loc).strip():
        return str(loc).strip()

    tags = row.get("Tags")
    if pd.notna(tags) and "fulfilled-by:" in str(tags):
        return str(tags).split("fulfilled-by:", 1)[1].split(",")[0].strip()

    return None


def assign_order_locations(df: pd.DataFrame) -> pd.Series:
    if "Name" not in df.columns:
        raise ValueError("CSV missing required column: Name")

    df = df.copy()
    df["_location_raw"] = df.apply(resolve_location, axis=1)

    # Forward-fill location within each order
    df["_location_raw"] = (
        df.groupby("Name", sort=False)["_location_raw"]
        .transform(lambda s: s.ffill().bfill())
    )

    missing = df["_location_raw"].isna() | (df["_location_raw"].str.strip() == "")
    if missing.any():
        logger.info(
            "%s rows (%s orders) have no location — will go to no_location file",
            int(missing.sum()),
            df.loc[missing, "Name"].nunique(),
        )

    return df["_location_raw"]


def discover_input_files(input_dir: Path) -> list[Path]:
    if not input_dir.is_dir():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    files = sorted(
        p
        for p in input_dir.glob("*.csv")
        if p.is_file()
        and not OUTPUT_PATTERN.match(p.name)
        and not NO_LOCATION_OUTPUT_PATTERN.match(p.name)
    )
    return files


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Split raw Shopify export CSVs into per-location files."
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        default=str(DEFAULT_INPUT_DIR),
        help=f"Folder with raw Shopify exports (default: {DEFAULT_INPUT_DIR})",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(DEFAULT_OUTPUT_DIR),
        help=f"Folder for split files (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--period",
        type=str,
        default=DEFAULT_PERIOD,
        help=f"Period suffix in output filename (default: {DEFAULT_PERIOD})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be written without creating files",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    try:
        input_files = discover_input_files(input_dir)
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 1

    if not input_files:
        logger.error("No raw CSV files found in %s", input_dir)
        return 1

    logger.info("Reading %s raw file(s) from %s", len(input_files), input_dir)
    frames = [read_csv(path) for path in input_files]
    combined = pd.concat(frames, ignore_index=True)
    logger.info("Combined rows: %s", f"{len(combined):,}")

    combined["_location_raw"] = assign_order_locations(combined)

    has_location = combined["_location_raw"].notna() & (
        combined["_location_raw"].str.strip() != ""
    )
    located = combined[has_location].copy()
    no_location = combined[~has_location].copy()

    output_dir.mkdir(parents=True, exist_ok=True)
    summary = []

    def write_group(group: pd.DataFrame, filename: str, label: str) -> None:
        if group.empty:
            return
        output_path = output_dir / filename
        out_df = group.drop(columns=["_location_raw"], errors="ignore")
        out_df = out_df.drop(columns=["_location_slug"], errors="ignore")
        summary.append({
            "location": label,
            "slug": filename.replace(".csv", ""),
            "rows": len(out_df),
            "orders": out_df["Name"].nunique(),
            "file": str(output_path),
        })
        if args.dry_run:
            logger.info(
                "Would write %s — %s rows, %s orders (%s)",
                filename,
                len(out_df),
                out_df["Name"].nunique(),
                label,
            )
        else:
            out_df.to_csv(output_path, index=False, encoding="utf-8")
            logger.info(
                "Wrote %s — %s rows, %s orders (%s)",
                filename,
                len(out_df),
                out_df["Name"].nunique(),
                label,
            )

    if not located.empty:
        located["_location_slug"] = located["_location_raw"].map(location_to_slug)
        for location_raw, group in located.groupby("_location_raw", sort=True):
            slug = location_to_slug(location_raw)
            filename = f"orders_export_{slug}_{args.period}.csv"
            write_group(group, filename, location_raw)

    if not no_location.empty:
        filename = f"orders_export_{NO_LOCATION_SLUG}_{args.period}.csv"
        write_group(no_location, filename, "no location")

    logger.info("")
    logger.info("=== SUMMARY ===")
    for row in summary:
        logger.info(
            "  %-25s -> %s (%s orders, %s rows)",
            row["location"],
            Path(row["file"]).name,
            row["orders"],
            row["rows"],
        )
    logger.info("Total locations: %s", len(summary))

    return 0


if __name__ == "__main__":
    sys.exit(main())
