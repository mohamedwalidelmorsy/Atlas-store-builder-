 HEAD
# Shopify Store Automation System

A complete automation system for creating and setting up Shopify stores automatically.

---

## Overview

This system fully automates the entire process of creating a Shopify store from scratch to delivery to the client:

1. **Store Creation** - Creates a new Development Store
2. **API Token Acquisition** - Creates an app and obtains API permissions
3. **Product Import** - Fetches products from eBay and uploads them to the store
4. **Ownership Transfer** - Transfers store ownership to the client

---

## Project Structure

```
shopify-automation/
├── app.py                      # Main Flask Application
├── requirements.txt            # Required Libraries
├── .env                        # Credentials and Settings
├── .gitignore                  # Git ignore rules
│
├── services/                   # Core Services
│   ├── config.py               # Settings Manager
│   ├── createStore.py          # Create Store (Selenium)
│   ├── accessToken.py          # Get API Token
│   ├── product.py              # Import Products
│   └── transferOwner.py        # Transfer Ownership
│
├── templates/                  # Web Pages
│   ├── index.html              # Home Page
│   ├── success.html            # Success Page
│   ├── error.html              # Error Page
│   └── history.html            # History Page
│
├── database/                   # Database
│   └── automation_progress.json
│
└── reports/                    # CSV Reports
    └── product_import_*.csv
```

---

## API Endpoints

### Web Routes

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Home Page (Form) |
| `/history` | GET | Automation History Page |
| `/create-store` | POST | Start Automation (Form-based) |

### REST API (For Frontend)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/stores` | POST | Create Store (Returns store_id immediately) |
| `/api/stores/<store_id>/status` | GET | Get Status (For polling) |
| `/api/status/<id>` | GET | Get Status by ID |
| `/api/history` | GET | All Records (JSON) |
| `/api/stats` | GET | System Statistics |

### POST /api/stores - Request

```json
{
  "client_name": "John Doe",
  "store_name": "my-store",
  "email": "john@example.com",
  "business_type": "ecommerce",
  "product_count": 5
}
```

### POST /api/stores - Response (202 Accepted)

```json
{
  "store_id": "abc12345",
  "status": "processing",
  "message": "Store creation started"
}
```

### GET /api/stores/{id}/status - Response

```json
{
  "store_id": "abc12345",
  "status": "processing|completed|failed",
  "current_step": "create_account|access_token|import_products|transfer_ownership",
  "message": "Creating your store...",
  "progress_percent": 25,
  "store_url": "https://store.myshopify.com",
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
│  • Create Development Store                                 │
│  • Change password to "1234"                                │
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
│  • Get Access Token (OAuth)                                 │
│  • Return: access_token                                     │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│               Step 3: product.py (50-75%)                   │
│  • Fetch products from TheScraper API                       │
│  • Filter & Score products                                  │
│  • Request Image Enhancement                                │
│  • Upload to Shopify via GraphQL                            │
│  • Return: imported_product_ids                             │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│             Step 4: transferOwner.py (75-100%)              │
│  • Login to Shopify Partners                                │
│  • Find store                                               │
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

## Configuration (.env)

```env
# Shopify Partners Credentials
SHOPIFY_DEV_EMAIL=your_email@gmail.com
SHOPIFY_DEV_PASSWORD=your_password

# Shopify API
SHOPIFY_API_VERSION=2024-01
```

---

## Supported Categories

- `iphone` - iPhone phones
- `samsung` - Samsung phones
- `ipad` - iPad tablets
- `tablet` - Other tablets
- `apple_watch` - Apple Watch
- `airpods` - AirPods
- `charger` - Chargers and cables
- `phone_cases` - Phone cases
- `power_bank` - Power banks
- `headphones` - Headphones

### Product Count

- Minimum: 5 products
- Maximum: 50 products
- Default: 5 products (V1)

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

---

## Database Schema

### File: `database/automation_progress.json`

```json
{
  "store_id": "abc12345",
  "id": 1,
  "timestamp": "2026-01-15 14:30:00",
  "user_data": {
    "client_name": "John Doe",
    "email": "customer@example.com",
    "store_name": "My Store",
    "country": "US",
    "product_category": "phone_cases",
    "product_count": 5
  },
  "status": "completed|processing|failed",
  "current_step": "create_account|access_token|import_products|transfer_ownership",
  "message": "Your store is ready!",
  "progress_percent": 100,
  "store_url": "https://xxx.myshopify.com",
  "admin_url": "https://admin.shopify.com/store/xxx",
  "products_imported": 5,
  "completed_at": "2026-01-15 15:00:00"
}
```

---

## Human-Like Automation Features

To avoid detection and blocking:

| Feature | Description |
|---------|-------------|
| **Random Delays** | 0.3-3.5 second delays |
| **Character Typing** | Types character by character |
| **Hesitation Pauses** | Random thinking pauses |
| **Stealth Mode** | Hides WebDriver detection |
| **Window Size** | 1280x800 (natural size) |
| **No Headless** | Avoids headless mode |

---

## Error Handling

- Try-catch in every service
- Browser auto-closes on error
- Screenshots saved on critical errors
- All operations logged to JSON

---

## Important Files

| File | Purpose |
|------|---------|
| `app.py` | Main entry point + API endpoints |
| `services/createStore.py` | Store creation |
| `services/accessToken.py` | Token acquisition |
| `services/product.py` | Product import |
| `services/transferOwner.py` | Ownership transfer |
| `.env` | Credentials |

---

## Links

- **TheScraper API:** `http://199.192.25.89:5000`
- **Shopify Partners:** `https://partners.shopify.com`
- **Shopify Admin:** `https://admin.shopify.com`
=======
# Atlas-store-builder-
AI-powered store builder that automatically creates, configures, and deploys e-commerce stores with smart product selection and optimization.
