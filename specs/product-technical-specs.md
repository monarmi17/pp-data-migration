## **Product Catalog Dataset \- Technical Specification**

## **Dataset Structure**

* Type: Shopify product variant catalog dataset  
* Granularity: Product variant level (each row \= one SKU variant)  
* Records: 9 product variants across multiple product families  
* Format: CSV with 67 columns

## **Key Identifiers**

* Primary Key: SKU (unique stock-keeping unit identifier)  
* Secondary Key: Product Code (unique product identifier)  
* Grouping Key: CID (appears to be consistent at 101818 for all records)  
* Product Grouping: Product variants can be grouped by base product name (derived from Product Name by removing size suffix)

## **Schema Overview**

Core Product Fields:

* CID (int): Customer/Company ID  
* Product Name (str): Full variant display name including size  
* SKU (str): Unique stock-keeping unit identifier  
* Previous SKU (str): Legacy SKU reference (mostly empty)  
* Product Code (int): Unique numeric product identifier

Pricing & Inventory:

* Price (float): Retail price  
* Price Unit (str): Currency/unit specification (empty in sample)  
* Member Price (float): Member discount price (empty in sample)  
* Cost (float): Cost basis for margin calculations  
* Stock Quantity (int): Current inventory level (all 0 in sample)  
* Min. reorder point (int): Minimum stock threshold  
* Max. reorder point (int): Maximum stock threshold (empty in sample)

Categorization:

* Category (str): Hierarchical category path (e.g., "Dog \>\> Dog Food \>\> Dog Kibble (Dry)")  
* Category code (int): Numeric category identifier  
* Vendor Name (str): Supplier name  
* Vendor Code (str): Supplier identifier  
* Brand name (str): Product brand  
* Brand code (str): Brand identifier

E-commerce Configuration:

* Allow Ship (bool): Shipping eligibility  
* Allow Pickup (bool): Store pickup eligibility  
* Sell online (bool): Online sales enabled  
* Track Inventory (bool): Inventory tracking enabled

Product Content:

* Short description (str): Brief product summary (mostly empty)  
* Long Description (str): Detailed HTML product description  
* Keywords (str): SEO keywords (mostly empty)  
* Tags (str): Product tags (mostly empty)  
* Image Url (str): Primary product image URL  
* Additional Image 1-3 Url (str): Secondary product images

Variant Relationships:

* Product variants (str): Comma-separated list of related SKUs  
* Is Matrix (bool): Indicates if product has variants

Promotional Fields:

* Sale start date (str): Promotion start date (DD/MM/YYYY format)  
* Sale end date (str): Promotion end date (DD/MM/YYYY format)  
* Sale price (float): Promotional pricing  
* Discontinue (bool): Product discontinuation status

## **Data Characteristics**

* Product Families: 6 distinct product groups (Dr Elseys, Champion-Acana variants, Nylabone, Simple Solution)  
* Primary Variant Dimension: Size (extracted from Product Name)  
* Categories: Pet supplies (litter, dog food, toys, cleaners)  
* Vendors: 3 suppliers (Trueman Distribution Ltd., Anipet Animal Supplies, Pan Pacific Pet)  
* Brands: 5 brands (Dr Elsey's, ACANA, Nylabone, Simple Solution)  
* Price Range: $15.99 \- $109.99  
* Active Promotions: 4 products with current sale pricing

## **Analysis Considerations**

* Product Grouping: Extract base product name by removing size suffix from Product Name  
* Variant Analysis: Use "Product variants" field to identify related SKUs  
* Pricing Analysis: Compare Price vs Sale price for promotional impact  
* Inventory Management: Min. reorder point indicates restocking thresholds  
* Category Performance: Use hierarchical Category field for segment analysis  
* Vendor Relationships: Group by Vendor Code for supplier analysis  
* Content Completeness: Long Description contains rich HTML content; Short description mostly empty

## **Technical Notes**

* Boolean fields use TRUE/FALSE string values (not native booleans)  
* HTML content in Long Description includes tables and formatting  
* Image URLs point to Azure blob storage  
* Comma-separated values in variant relationships require parsing  
* Date fields use DD/MM/YYYY format where present

