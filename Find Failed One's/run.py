import os
import pandas as pd

# --- STEP 1: Take inputs from user ---
input_file = input("Enter Excel filename (e.g., orders.xlsx): ").strip()

# --- STEP 2: Validate input file ---
if not os.path.exists(input_file):
    print(f"❌ File not found: {input_file}")
    print("💡 Make sure the file is in the same folder as this script or provide the full path.")
    exit()

# --- STEP 3: Build output filename automatically ---
base_name, ext = os.path.splitext(os.path.basename(input_file))
output_file = f"{base_name}_failed{ext}"

try:
    # --- STEP 4: Read Excel file ---
    ext = os.path.splitext(input_file)[1].lower()

    if ext in [".xlsx", ".xls"]:
        df = pd.read_excel(input_file)
    elif ext == ".csv":
        df = pd.read_csv(input_file)
    else:
        print("❌ Unsupported file type. Please provide .xlsx, .xls, or .csv")
        exit()

    # --- STEP 5: Validate column presence ---
    if "Import Result" not in df.columns:
        print("❌ 'Import Result' column not found in the Excel file.")
        exit()

    # Detect order ID column
    possible_keys = ["Name", "Order Name", "Ticket", "Ticket ID", "ID (Ref)"]
    key_column = next((col for col in possible_keys if col in df.columns), None)

    if not key_column:
        print("❌ Could not find an order/ticket ID column (e.g., 'Name' or 'ID (Ref)').")
        exit()

    # --- STEP 6: Normalize data ---
    df["Import Result"] = df["Import Result"].astype(str).str.strip().str.lower()
    df[key_column] = df[key_column].astype(str).str.strip()

    # --- STEP 7: Find all orders that have *any* failed line ---
    failed_ids = df.loc[df["Import Result"] == "failed", key_column].unique()

    if len(failed_ids) == 0:
        print("✅ No failed rows found.")
        exit()

    # --- STEP 8: Get *all* rows belonging to those failed orders ---
    related_rows = df[df[key_column].isin(failed_ids)]

    # STEP 8.1: Sanitize output columns
    columns_to_exclude = [
        "ID (Ref)",
        "Name (Ref)",
        "Import Result",
        "Import Comment",
        "Line: Variant Barcode",
        "Line: SKU"
    ]

    related_rows = related_rows.drop(
        columns=[col for col in columns_to_exclude if col in related_rows.columns]
    )

    # --- STEP 9: Save results to new Excel file ---
    output_path = os.path.join(os.getcwd(), output_file)
    if ext in [".xlsx", ".xls"]:
        related_rows.to_excel(output_path, index=False)
    elif ext == ".csv":
        related_rows.to_csv(output_path, index=False)


    print(f"✅ Found {len(failed_ids)} orders with at least one failed line.")
    print(f"🧾 Exported {len(related_rows)} total rows (all lines from those orders).")
    print(f"💾 Saved to: {output_path}")

except Exception as e:
    print(f"⚠️ Error processing file: {e}")
