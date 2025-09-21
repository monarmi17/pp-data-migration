## **Product Catalog Dataset \- Technical Specification**

## **Dataset Structure**

- Type: Shopify product variant catalog dataset
- Granularity: Product variant level (each row \= one SKU variant)
- Records: 11,498 product variants across multiple product families
- Format: Excel (.xlsx) with 74 columns

## **Key Identifiers**

- Primary Key: SKU (unique stock-keeping unit identifier) - 11,498 unique values
- Secondary Key: Product Code (unique product identifier) - 11,003 unique values (241 nulls)
- Grouping Key: CID (consistent at 101818 for all records)
- Product Grouping: Product variants can be grouped by base product name (derived from Product Name by removing size suffix)

## **Schema Overview**

Core Product Fields:

- CID (int): Customer/Company ID - All records have value 101818
- Product Name (str): Full variant display name including size - 11,355 unique values
- SKU (str): Unique stock-keeping unit identifier - 11,498 unique values
- Previous SKU (float): Legacy SKU reference - All values are null/empty
- Product Code (str): Unique product identifier - 11,003 unique values (241 nulls)

Pricing & Inventory:

- Price (float): Retail price - Range: $0.00 - $629.99, Average: $30.52, Median: $20.99
- Price Unit (str): Currency/unit specification - Only 5 records have value "g", rest are null
- Member Price (float): Member discount price - Only 5 records have value 0.0, rest are null
- Cost (float): Cost basis for margin calculations - 11,489 records have values (9 nulls), 4,327 unique values
- Stock Quantity (int): Current inventory level - Values: 0, 44, 47, 19 (mostly 0)
- Min. reorder point (int): Minimum stock threshold - 10,986 records have values (512 nulls), 40 unique values
- Max. reorder point (int): Maximum stock threshold - All values are null/empty

Categorization:

- Category (str): Hierarchical category path - 78 unique categories including "Dog >> Dog Food >> Dog Kibble (Dry)", "Cat >> Cat Food >> Cat Canned (Wet)", "Health and Wellness >> Collars Leashes & Harnesses", etc.
- Category code (int): Numeric category identifier - 78 unique values matching categories
- Vendor Name (str): Supplier name - 26 unique vendors, 419 nulls
- Vendor Code (str): Supplier identifier - 26 unique values matching vendor names
- Brand name (str): Product brand - 304 unique brands, 10 nulls
- Brand code (str): Brand identifier - 304 unique values matching brand names
- Tax category (str): Tax classification - Values: "Sales Tax", "none" (229 nulls)

E-commerce Configuration:

- Allow Ship (bool): Shipping eligibility - True: 11,477, False: 21
- Allow Pickup (bool): Store pickup eligibility - All records: True
- Sell online (bool): Online sales enabled - True: 9,452, False: 2,046
- Track Inventory (bool): Inventory tracking enabled - True: 11,467, False: 31
- Allow Deliver (bool): Delivery eligibility - True: 11,477, False: 21
- Show on SmartShelf (bool): Smart shelf display - True: 11,477, False: 21
- Enable subscription (bool): Subscription capability - All records: False

Product Content:

- Short description (str): Brief product summary - 310 records have values (11,188 nulls), 229 unique values
- Long Description (str): Detailed HTML product description - 9,758 records have values (1,740 nulls), 6,459 unique values
- Keywords (str): SEO keywords - 248 records have values (11,250 nulls), 170 unique values
- Tags (str): Product tags - 846 records have values (10,652 nulls), 205 unique values
- Image Url (str): Primary product image URL - 9,897 records have values (1,601 nulls), all unique
- Additional Image 1-3 Url (str): Secondary product images - 1,920, 527, 198 records respectively

Variant Relationships:

- Product variants (str): Comma-separated list of related SKUs - 168 records have values (11,330 nulls)
- Is Matrix (bool): Indicates if product has variants - All records: False
- Impulse buy (str): Comma-separated list of impulse buy SKUs - 650 records have values (10,848 nulls), 94 unique values

Promotional Fields:

- Sale start date (str): Promotion start date - 1,425 records have values (10,073 nulls), 63 unique dates
- Sale end date (str): Promotion end date - 1,425 records have values (10,073 nulls), 68 unique dates
- Sale price (float): Promotional pricing - 1,425 records have values (10,073 nulls), Range: $0.05 - $184.99
- Discontinue (bool): Product discontinuation status - False: 11,446, True: 52
- Eligible for manual discount (bool): Manual discount eligibility - True: 11,477, False: 21
- Eligible for automated discount (bool): Automated discount eligibility - True: 11,477, False: 21

Additional Fields:

- SKU type (str): SKU classification - All records: "Long"
- Qualified for installment (bool): Installment payment eligibility - All records: False
- Allow Price Override (bool): Price override capability - True: 11,477, False: 21
- Allow negative quantity in store pickup (bool): Negative quantity allowance - True: 11,477, False: 21
- Not for sale (bool): Sales restriction - All records: False
- Add Serial Number (bool): Serial number requirement - All records: False
- EBT Qualified (bool): EBT payment eligibility - All records: False
- Pay by membership (bool): Membership payment - All records: False
- Weight/Width/Height/Length (float): Physical dimensions - All records: 0
- Use vendor info for frequent feeder (bool): Vendor info usage - All records: False

## **Data Characteristics**

- Product Families: 11,355 unique product names across multiple categories
- Primary Variant Dimension: Size (extracted from Product Name)
- Categories: 78 hierarchical categories covering pet supplies (dog food, cat food, toys, health & wellness, etc.)
- Top Categories: "Health and Wellness >> Collars Leashes & Harnesses" (2,326 products), "Dog >> Dog Toy >> Dog Plush" (1,030 products), "Safety >> Wearables" (1,166 products)
- Vendors: 26 suppliers including PETSlink Distribution Ltd. (4,124 products), RC Pets (2,317 products), Anipet Animal Supplies (1,444 products)
- Brands: 304 brands including RC Pet (2,317 products), KONG (590 products), Coastal (397 products)
- Price Range: $0.00 - $629.99 (Average: $30.52, Median: $20.99)
- Active Promotions: 1,425 products with current sale pricing (12.4% of catalog)

## **Analysis Considerations**

- Product Grouping: Extract base product name by removing size suffix from Product Name
- Variant Analysis: Use "Product variants" field to identify related SKUs (168 products have variant relationships)
- Pricing Analysis: Compare Price vs Sale price for promotional impact (1,425 products on sale)
- Inventory Management: Min. reorder point indicates restocking thresholds (10,986 products have reorder points)
- Category Performance: Use hierarchical Category field for segment analysis (78 categories)
- Vendor Relationships: Group by Vendor Code for supplier analysis (26 vendors)
- Content Completeness: Long Description contains rich HTML content (9,758 products); Short description mostly empty (310 products)
- Image Management: Primary images available for 9,897 products, additional images for subset
- E-commerce Readiness: 9,452 products enabled for online sales, 2,046 offline-only
- Discontinued Products: 52 products marked for discontinuation

## **Technical Notes**

- Boolean fields use native boolean values (True/False)
- HTML content in Long Description includes tables and formatting
- Image URLs point to external storage (likely Azure blob storage)
- Comma-separated values in variant relationships require parsing
- Date fields use DD/MM/YYYY format where present
- Product Code field has 241 null values requiring data cleaning
- Many optional fields are predominantly null (Previous SKU, Max. reorder point, etc.)
- Physical dimensions (Weight, Width, Height, Length) are all set to 0
- SKU type is consistently "Long" across all records
- Most products (11,477) are configured for shipping and pickup
- Subscription functionality is disabled for all products
