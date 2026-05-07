# Atlas Store Builder

A complete automation system for creating and setting up Shopify stores automatically with product import, image enhancement, and email reporting.

---

## Overview

This system fully automates the entire process of creating a Shopify store from scratch to delivery to the client:

1. **Store Creation** - Creates a new Development Store with name format `{name}.ts-scout`
2. **API Token Acquisition** - Creates an app and obtains API permissions via Client Credentials Grant
3. **Product Import** - Fetches products from API, scores & filters them, uploads to Shopify
4. **Hero Image Setup** - Uploads a banner image to the store's homepage via GraphQL Admin API
5. **Email Report** - Sends a CSV report with imported products to the customer
6. **Ownership Transfer** - Transfers store ownership to the client via Partners dashboard

---

## Project Structure

```
Atlas-store-builder/
├── app.py                          # Main Flask Application
├── requirements.txt                # Required Libraries
├── .env                            # Credentials and Settings
├── .gitignore                      # Git ignore rules
│
├── services/                       # Core Services (Modular)
│   ├── config.py                   # Settings Manager
│   ├── createStore.py              # Store Creation (Selenium)
│   ├── accessToken.py              # API Token Acquisition
│   ├── transferOwner.py            # Ownership Transfer
│   │
│   ├── product.py                  # Product Import Orchestrator
│   ├── product_loader.py           # API Loading & Keywords
│   ├── product_scoring.py          # Scoring & Filtering
│   ├── product_images.py           # Image Extraction & Enhancement
│   ├── product_processing.py       # Parsing, Titles & Descriptions
│   ├── product_upload.py           # Shopify Upload & Hero Image
│   └── product_report.py           # CSV Reports & Email
│
├── templates/                      # Frontend Pages
│   ├── base.html                   # Base template (shared layout)
│   ├── create.html                 # Store creation form
│   ├── processing.html             # Real-time progress page
│   ├── success.html                # Success page with store details
│   ├── error.html                  # Error page
│   ├── history.html                # Automation history
│   └── layout/                     # Reusable layout components
│       ├── header.html             # Navigation header
│       ├── sidebar.html            # Sidebar navigation
│       └── footer.html             # Page footer
│
├── static/                         # Static Assets
│   ├── css/                        # Stylesheets
│   │   ├── base.css                # Global styles
│   │   ├── create.css              # Create form styles
│   │   ├── processing.css          # Progress page styles
│   │   ├── success.css             # Success page styles
│   │   ├── header.css              # Header styles
│   │   ├── sidebar.css             # Sidebar styles
│   │   └── footer.css              # Footer styles
│   ├── images/                     # Logos & icons
│   │   ├── logo.svg
│   │   └── Scout-Logo 20x20-01.svg
│   └── js/                         # JavaScript libraries
│       ├── bootstrap.min.js
│       └── jquery-3.7.1.min.js
│
├── data/                           # Generated Data
│   ├── reports/                    # CSV product import reports
│   ├── screenshots/                # Error screenshots for debugging
│   └── photo/                      # Hero/banner images for stores
│
└── database/                       # Database
    └── automation_progress.json
```

---

## Product Import - Modular Architecture

The product import system is split into 6 specialized modules using the **Mixin pattern**. Each module handles a specific responsibility, and the main `EbayShopifyImporter` class inherits from all of them:

```python
class EbayShopifyImporter(
    ProductLoaderMixin,      # API loading & keywords
    ProductScoringMixin,     # Scoring & filtering
    ProductImagesMixin,      # Image extraction & enhancement
    ProductProcessingMixin,  # Parsing, titles & descriptions
    ProductUploadMixin,      # Shopify upload & hero image
    ProductReportMixin       # CSV reports & email
):
```

| Module | File | Responsibility |
|--------|------|----------------|
| **Loader** | `product_loader.py` | Fetch products from API, keyword mapping, fallback loading |
| **Scoring** | `product_scoring.py` | Relevance scoring, quality scoring, smart selection with fallback |
| **Images** | `product_images.py` | Image extraction (6-step), enhancement via API, validation, dedup |
| **Processing** | `product_processing.py` | Title rewriting, professional descriptions, price/SKU extraction |
| **Upload** | `product_upload.py` | Shopify product upload, hero/banner image upload via GraphQL |
| **Report** | `product_report.py` | CSV report generation, HTML email with SMTP |

---

## Frontend

The frontend uses a **component-based template** structure with Bootstrap and jQuery:

- **Base Template** (`base.html`) - Shared layout with header, sidebar, and footer
- **Create Page** (`create.html`) - Store creation form with category selection, product count, and client details
- **Processing Page** (`processing.html`) - Real-time progress tracking with status polling
- **Success Page** (`success.html`) - Displays store URL, admin access, and import summary
- **Error Page** (`error.html`) - Error details with retry options
- **History Page** (`history.html`) - List of all automation runs with status

Layout components (`header.html`, `sidebar.html`, `footer.html`) are reusable across all pages. Each page has its own dedicated CSS file for styling.

---

## Store Creation Details

### Store Name Format
- Format: `{name}.ts-scout` (e.g., `ahmed.ts-scout`)
- If the name is taken, retries with random numbers: `ahmed517.ts-scout`
- The input field is properly cleared between retry attempts

### Store Password
- Default password: `ts-scout1234`
- Changed via Shopify's iframe-based password settings page

---

## API Endpoints

### Web Routes

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Redirects to `/create` |
| `/create` | GET | Store creation form |
| `/processing/<store_id>` | GET | Real-time progress page (polls `/api/stores/<store_id>/status`) |
| `/success` | GET | Success page (query params: `store_url`, `store_name`, `products_count`, `customer_email`) |
| `/history` | GET | Automation history page |

### Form Submission (Synchronous)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/create-store` | POST | Run full automation synchronously; renders `success.html` or `error.html` on completion |

### REST API (Asynchronous)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/stores` | POST | Start automation in background thread; returns `store_id` immediately (202) |
| `/api/stores/<store_id>/status` | GET | Poll status by UUID `store_id` |
| `/api/status/<int:id>` | GET | Get status by integer record ID (legacy) |
| `/api/history` | GET | All records (JSON) |
| `/api/stats` | GET | System statistics |

### POST /api/stores - Request

```json
{
  "client_name": "John Doe",
  "store_name": "my-store",
  "email": "john@example.com",
  "product_category": "iphone",
  "product_count": 5,
  "country": "US"
}
```

> **Required fields:** `client_name`, `store_name`, `email`, `product_category`.  
> `business_type` is hardcoded to `"ecommerce"`. `product_count` is forced to `5` in API V1.

### POST /api/stores - Response (202 Accepted)

```json
{
  "store_id": "abc12345",
  "status": "processing",
  "message": "Store creation started"
}
```

### GET /api/stores/{store_id}/status - Response

```json
{
  "store_id": "abc12345",
  "status": "processing|completed|failed",
  "current_step": "queued|create_account|access_token|import_products|transfer_ownership|completed",
  "message": "Creating your store...",
  "progress_percent": 25,
  "store_url": "https://store.myshopify.com",
  "admin_url": "https://store.myshopify.com/admin",
  "products_imported": 5,
  "store_password": "ts-scout1234",
  "error": "Error message (if failed)"
}
```

---

## Automation Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    User Input (Web Form)                    │
│  [Email, Store Name, Country, Category, Product Count]      │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Step 1: createStore.py (0-25%)                 │
│  • Login to Shopify Partners                                │
│  • Create Development Store ({name}.ts-scout)               │
│  • Change password to "ts-scout1234" (iframe-based)         │
│  • Return: store_url, store_id, browser_session             │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Step 2: accessToken.py (25-50%)                │
│  • Use same browser session                                 │
│  • Create App in Dev Dashboard                              │
│  • Configure API Scopes                                     │
│  • Release App & Install to Store                           │
│  • Get Access Token (Client Credentials Grant)              │
│  • Close browser                                            │
│  • Return: access_token                                     │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│            Step 3: Product Import (50-75%)                  │
│  • Fetch products from API (product_loader.py)              │
│  • Score & select best products (product_scoring.py)        │
│  • Extract & enhance images (product_images.py)             │
│  • Rewrite titles & descriptions (product_processing.py)    │
│  • Upload to Shopify REST API (product_upload.py)           │
│  • Upload hero banner via GraphQL (product_upload.py)       │
│  • Generate CSV report & send email (product_report.py)     │
│  • Return: imported_product_ids                             │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│             Step 4: transferOwner.py (75-100%)              │
│  • Login to Shopify Partners (new browser session)          │
│  • Find store by base name                                  │
│  • Transfer ownership to customer email                     │
│  • Return: transfer_status                                  │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Final Output                            │
│  • Save to automation_progress.json                         │
│  • Show success page with store URL                         │
└─────────────────────────────────────────────────────────────┘
```

---

## Hero/Banner Image — GraphQL Upload Flow

The system uploads a hero banner image to the store's homepage using the **Shopify GraphQL Admin API**. It never modifies Liquid files.

### Steps

1. Read image from `data/photo/` (supports PNG, JPG, JPEG, WEBP)
2. `stagedUploadsCreate` mutation → get staged upload URL + parameters
3. POST binary via `multipart/form-data` to staged URL
4. `fileCreate` mutation with `resourceUrl`
5. Poll `node(id)` query until `fileStatus == READY`; extract CDN URL
6. Build file reference: `shopify://shop_images/{filename}`
7. Fetch active theme ID + `templates/index.json`
8. Locate hero section (checks types: `image-banner`, `image_banner`, `hero`, `slideshow`, `banner`)
9. Resolve `image_picker` setting ID from `sections/{type}.liquid` schema
10. Write setting + PUT `templates/index.json` back to Shopify; verify persistence

> **Note:** If no hero section is found in `templates/index.json`, the upload step is skipped (returns `False`) without modifying the theme.

---

## Email Reports (SMTP)

After importing products, the system sends an HTML email report with an attached CSV file.

### Email Content
- HTML email with product summary table (count, total value, avg margin, avg score)
- Up to 10 products listed with price and quality score
- Attached CSV file with full product details
- Plain text fallback for non-HTML email clients

---

## Configuration (.env)

```env
# Shopify Partners Credentials (required)
SHOPIFY_DEV_EMAIL=your_email@gmail.com
SHOPIFY_DEV_PASSWORD=your_password

# Shopify Partners Organization ID (optional, has default)
SHOPIFY_PARTNER_ID=4498869

# Flask
SECRET_KEY=your-secret-key-here

# SMTP Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
FROM_EMAIL=your_email@gmail.com
FROM_NAME=Product Import System
CUSTOMER_EMAIL=customer@example.com

# Reports
REPORTS_DIR=data/reports
```

> `SHOPIFY_API_VERSION` is hardcoded to `2024-01` in `product.py` and is not read from `.env`.  
> For Gmail SMTP, use an [App Password](https://support.google.com/accounts/answer/185833).

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SHOPIFY_DEV_EMAIL` | Yes | — | Shopify Partners account email |
| `SHOPIFY_DEV_PASSWORD` | Yes | — | Shopify Partners account password |
| `SHOPIFY_PARTNER_ID` | No | `4498869` | Partners org ID for ownership transfer |
| `SECRET_KEY` | No | `your-secret-key-here` | Flask session secret |
| `SMTP_SERVER` | No | `smtp.gmail.com` | SMTP host |
| `SMTP_PORT` | No | `587` | SMTP port |
| `SMTP_USERNAME` | No | — | SMTP login |
| `SMTP_PASSWORD` | No | — | SMTP password / App Password |
| `FROM_EMAIL` | No | `noreply@yourstore.com` | Sender address |
| `FROM_NAME` | No | `Product Import System` | Sender display name |
| `REPORTS_DIR` | No | `data/reports` | Directory for CSV reports |

---

## TheScraper API Integration

### Server Info

```
Server: 199.192.25.89
Port: 5000
Protocol: HTTP
```

### Endpoints Used

| Endpoint | Description |
|----------|-------------|
| `GET /api/category/<name>?limit=1000` | Fetch products by category |
| `POST /api/enhance` | Request image enhancement |
| `GET /api/enhanced/<item_id>` | Get enhanced product |

---

## Supported Categories

| Key | Label |
|-----|-------|
| `iphone` | iPhone phones |
| `samsung` | Samsung phones |
| `ipad` | iPad tablets |
| `tablet` | Other tablets |
| `apple_watch` | Apple Watch |
| `airpods` | AirPods |
| `charger` | Chargers and cables |
| `phone_cases` | Phone cases |
| `power_bank` | Power banks |
| `headphones` | Headphones |

### Product Count

- Effective range (form): 1 – 50 (validated in `app.py`)
- Effective range (importer): 5 – 30 (clamped in `EbayShopifyImporter.__init__`)
- API V1 (`/api/stores`): forced to 5

---

## Smart Product Selection (Score-Based System)

The system uses **ranking over filtering** to ensure products are always imported.

### Scoring System

| Signal | Score |
|--------|-------|
| `product_type == "case"` | +50 points |
| `product_type == "accessory"` | +20 points |
| Title contains "case/cover/shell" | +30 points each (max 60) |
| Title contains phone brand/model | +20 points each (max 40) |
| Required keyword match | +25 points |
| Positive keyword match | +15 points each (max 45) |
| Negative keywords | -15 points penalty (NOT rejection) |

### Smart Fallback (Never Zero Products)

1. **Fallback 1**: Relax penalties and rescore
2. **Fallback 2**: Expand allowed product types
3. **Fallback 3**: Use all products with minimal criteria
4. **Final Resort**: Random sample if all else fails

---

## Smart Title Rewriting

Transforms messy source titles into clean, professional product names:

**Before:**
```
Cheap Factory Hot Sale Shockproof Silicone Case For iPhone 15 Pro Max Wholesale
```

**After:**
```
Shockproof Silicone Case for iPhone 15 Pro Max
```

### Title Extraction

| Component | Examples |
|-----------|----------|
| **Brand/Model** | iPhone 16 Pro Max, Galaxy S24 Ultra, Pixel 8 |
| **Product Type** | Case, Charger, Cable, Screen Protector |
| **Features** | Shockproof, Slim, Clear, Magnetic, Leather |

---

## Installation & Running

### 1. Install Requirements

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your credentials
```

### 3. Run Application

```bash
python app.py
```

### 4. Open in Browser

```
http://localhost:5000
```

---

## Technology Stack

| Technology | Usage |
|------------|-------|
| **Python 3.13+** | Core language |
| **Flask 3.1.2** | Web Framework |
| **Selenium 4.39+** | Browser Automation |
| **Requests 2.32+** | HTTP Client |
| **python-dotenv 1.2+** | Environment Variables |
| **Bootstrap** | Frontend CSS framework |
| **jQuery 3.7.1** | Frontend JavaScript |

---

## Data Organization

All generated files are organized in the `data/` folder:

```
data/
├── reports/       # CSV product import reports
├── screenshots/   # Error screenshots for debugging
└── photo/         # Hero/banner images for stores
```

---

## Error Handling

- Try-catch in every service
- Browser auto-closes on error
- Screenshots saved on critical errors (no HTML page source files)
- All operations logged to `database/automation_progress.json`

---

## Important Files

| File | Purpose |
|------|---------|
| `app.py` | Main entry point, routes, background task runner |
| `services/createStore.py` | Store creation automation |
| `services/accessToken.py` | Token acquisition (Client Credentials Grant) |
| `services/product.py` | Product import orchestrator |
| `services/product_loader.py` | API loading & keywords |
| `services/product_scoring.py` | Product scoring & filtering |
| `services/product_images.py` | Image extraction & enhancement |
| `services/product_processing.py` | Title rewriting & descriptions |
| `services/product_upload.py` | Shopify REST upload & GraphQL hero image |
| `services/product_report.py` | CSV reports & email sending |
| `services/transferOwner.py` | Ownership transfer |
| `database/automation_progress.json` | All automation run records |
| `.env` | Credentials & SMTP config |

---

## Links

- **TheScraper API:** `http://199.192.25.89:5000`
- **Shopify Partners:** `https://partners.shopify.com`
- **Shopify Admin:** `https://admin.shopify.com`
