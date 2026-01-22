from flask import Flask, render_template, request, jsonify
from datetime import datetime
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
import uuid
import json
import os
import sys

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')

# Database file path
DB_PATH = 'database/automation_progress.json'

# Thread pool for background automation (max 3 concurrent automations)
executor = ThreadPoolExecutor(max_workers=3)

# ============================================================
# DATABASE FUNCTIONS
# ============================================================

def load_history():
    """Load automation history from JSON database"""
    try:
        if os.path.exists(DB_PATH):
            with open(DB_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
    except json.JSONDecodeError:
        print("Warning: Database file corrupted, creating new one")
        return []
    return []

def save_history(entry):
    """Save new automation entry to JSON database"""
    history = load_history()
    history.append(entry)

    os.makedirs('database', exist_ok=True)
    with open(DB_PATH, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=4, ensure_ascii=False)

def generate_store_id():
    """Generate unique store ID using UUID (8 characters)"""
    return str(uuid.uuid4())[:8]

def get_entry_by_store_id(store_id):
    """Get automation entry by generated store_id"""
    history = load_history()
    for entry in history:
        if entry.get('store_id') == store_id:
            return entry
    return None

def update_entry_status(store_id, updates):
    """Update entry status in database by store_id"""
    history = load_history()

    for entry in history:
        if entry.get('store_id') == store_id:
            entry.update(updates)
            break

    os.makedirs('database', exist_ok=True)
    with open(DB_PATH, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=4, ensure_ascii=False)

def validate_config():
    """Validate that required environment variables exist"""
    required = [
        'SHOPIFY_DEV_EMAIL',
        'SHOPIFY_DEV_PASSWORD'
    ]
    
    missing = [var for var in required if not os.getenv(var)]
    
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
    
    return True

# ============================================================
# ROUTES - PAGES
# ============================================================

@app.route('/')
def index():
    """Main page - user input form"""
    return render_template('index.html')

@app.route('/history')
def history():
    """Display history of all created stores"""
    history_data = load_history()
    return render_template('history.html', stores=history_data)

# ============================================================
# MAIN AUTOMATION WORKFLOW
# ============================================================

@app.route('/create-store', methods=['POST'])
def create_store():
    """
    Main automation workflow - orchestrates all services
    
    Flow:
    1. Validate user input
    2. Create Shopify store (returns store_data + driver)
    3. Get API access token (uses same driver)
    4. Import products from AliExpress
    5. Transfer ownership to customer
    6. Save to database
    """
    
    automation_log = None
    browser_session = None
    
    try:
        # ===== VALIDATE USER INPUT =====
        user_data = {
            'email': request.form.get('email', '').strip(),
            'store_name': request.form.get('store_name', '').strip(),
            'country': request.form.get('country', 'US').strip(),
            'business_type': request.form.get('business_type', 'ecommerce').strip(),
            'product_category': request.form.get('product_category', 'electronics').strip(),
            'product_count': int(request.form.get('product_count', 5))  # Added product count
        }

        # Validate required fields
        if not user_data['email']:
            raise ValueError("Email is required")
        if not user_data['store_name']:
            raise ValueError("Store Name is required")
        if '@' not in user_data['email']:
            raise ValueError("Invalid email format")
        
        # ✅ Validate product count
        if user_data['product_count'] < 1 or user_data['product_count'] > 50:
            raise ValueError("Product count must be between 1 and 50")

        # Initialize automation log
        automation_log = {
            'id': len(load_history()) + 1,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'user_data': user_data,
            'status': 'in_progress',
            'steps': [],
            'store_url': None,
            'store_id': None
        }

        print(f"\n{'='*70}")
        print(f"STARTING AUTOMATION FOR: {user_data['email']}")
        print(f"{'='*70}")

        # ===== STEP 1: Create Shopify Account =====
        print(f"\n[STEP 1/4] Creating Shopify store...")
        
        automation_log['steps'].append({
            'step': 'create_account',
            'status': 'started',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
        # Import and execute createStore service
        from services.createStore import ShopifyAccountCreator
        account_creator = ShopifyAccountCreator()
        
        # Receive TWO separate return values: store_data dict + driver object
        store_data, browser_session = account_creator.create_store(
            email=user_data['email'],
            store_name=user_data['store_name'],
            country=user_data['country'],
            business_type=user_data['business_type']
        )
        
        # Validate store creation result
        if not store_data or not store_data.get('store_url'):
            raise ValueError("Failed to create store: No store URL returned")
        
        # Verify browser session
        if not browser_session:
            raise ValueError("CRITICAL: No browser session received from createStore")
        
        print(f"Browser session received: {type(browser_session).__name__}")
        
        # Log clean store data (no driver in JSON)
        automation_log['steps'][-1]['status'] = 'completed'
        automation_log['steps'][-1]['data'] = {
            'store_url': store_data.get('store_url'),
            'store_id': store_data.get('store_id'),
            'admin_url': store_data.get('admin_url'),
            'created_at': store_data.get('created_at')
        }
        automation_log['store_url'] = store_data.get('store_url')
        automation_log['store_id'] = store_data.get('store_id')
        
        print(f"Store created: {store_data.get('store_url')}")

        # ===== STEP 2: Get Access Token =====
        print(f"\n[STEP 2/4] Retrieving API access token...")
        print(f"Passing browser session to accessToken...")
        
        automation_log['steps'].append({
            'step': 'access_token',
            'status': 'started',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
        # Import and execute accessToken service with existing browser
        from services.accessToken import AccessTokenManager
        token_manager = AccessTokenManager()
        
        # Call get_token with store_url and driver
        access_token = token_manager.get_token(
            store_url=store_data['store_url'],
            driver=browser_session  # Pass the WebDriver object
        )
        
        if not access_token:
            raise ValueError("Failed to retrieve access token")
        
        automation_log['steps'][-1]['status'] = 'completed'
        automation_log['steps'][-1]['token_created'] = True
        automation_log['steps'][-1]['token_preview'] = access_token[:15] + '...' if access_token else None
        
        print(f"Access token retrieved: {access_token[:15]}...")
        
        # Close browser after token extraction
        if browser_session:
            try:
                browser_session.quit()
                browser_session = None
                print("Browser closed after token extraction")
            except Exception as e:
                print(f"Warning: Failed to close browser: {str(e)}")

        # ===== STEP 3: Import Products from AliExpress =====
        print(f"\n[STEP 3/4] Importing {user_data['product_count']} products (category: {user_data['product_category']})...")
        
        automation_log['steps'].append({
            'step': 'import_products',
            'status': 'started',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
        # Import and execute product service
        from services.product import ProductImporter
        product_importer = ProductImporter(access_token, store_data['store_url'])
        imported_products = product_importer.import_products(
            category=user_data['product_category'],
            count=user_data['product_count']  # Pass user-specified count
        )
        
        automation_log['steps'][-1]['status'] = 'completed'
        automation_log['steps'][-1]['products_imported'] = len(imported_products)
        automation_log['steps'][-1]['category'] = user_data['product_category']
        automation_log['steps'][-1]['requested_count'] = user_data['product_count']  # Log requested count
        
        print(f"Imported {len(imported_products)} products")

        # ===== STEP 4: Transfer Ownership =====
        print(f"\n[STEP 4/4] Transferring ownership to {user_data['email']}...")
        
        automation_log['steps'].append({
            'step': 'transfer_ownership',
            'status': 'started',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
        # Import and execute transferOwner service
        from services.transferOwner import OwnershipTransfer
        ownership_transfer = OwnershipTransfer(access_token, store_data['store_url'])
        transfer_result = ownership_transfer.transfer_to_customer(user_data['email'])
        
        automation_log['steps'][-1]['status'] = 'completed'
        automation_log['steps'][-1]['data'] = transfer_result
        
        print(f"Ownership transferred successfully")

        # ===== MARK AS COMPLETED =====
        automation_log['status'] = 'completed'
        automation_log['completed_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Save to database
        save_history(automation_log)
        
        print(f"\n{'='*70}")
        print(f"AUTOMATION COMPLETED SUCCESSFULLY")
        print(f"{'='*70}")
        print(f"Store URL: {store_data['store_url']}")
        print(f"Products: {len(imported_products)}")
        print(f"Owner: {user_data['email']}")
        print(f"{'='*70}\n")

        # Render success page
        return render_template('success.html', 
                             store_url=store_data['store_url'],
                             store_name=user_data['store_name'],
                             products_count=len(imported_products),
                             customer_email=user_data['email'],
                             automation_log=automation_log)

    except Exception as e:
        # ===== ERROR HANDLING =====
        print(f"\n{'='*70}")
        print(f"AUTOMATION FAILED")
        print(f"{'='*70}")
        print(f"Error: {str(e)}")
        print(f"{'='*70}\n")
        
        # Ensure browser is closed on error
        if browser_session:
            try:
                browser_session.quit()
                print("Browser closed due to error")
            except:
                pass
        
        # Log the error
        if automation_log:
            automation_log['status'] = 'failed'
            automation_log['error'] = str(e)
            automation_log['failed_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            save_history(automation_log)
        
        # Render error page
        return render_template('error.html', 
                             error=str(e),
                             automation_log=automation_log)

# ============================================================
# API ENDPOINTS
# ============================================================

@app.route('/api/status/<int:store_id>')
def get_status(store_id):
    """API endpoint to check automation status by store ID"""
    history = load_history()
    for entry in history:
        if entry.get('id') == store_id:
            return jsonify(entry)
    return jsonify({'error': 'Store not found'}), 404

@app.route('/api/history')
def get_all_history():
    """API endpoint to get all automation history"""
    history = load_history()
    return jsonify({
        'total': len(history),
        'stores': history
    })

@app.route('/api/stats')
def get_stats():
    """API endpoint to get automation statistics"""
    history = load_history()
    
    total_stores = len(history)
    completed = sum(1 for entry in history if entry.get('status') == 'completed')
    failed = sum(1 for entry in history if entry.get('status') == 'failed')
    in_progress = sum(1 for entry in history if entry.get('status') == 'in_progress')
    
    total_products = sum(
        step.get('products_imported', 0) 
        for entry in history 
        for step in entry.get('steps', []) 
        if step.get('step') == 'import_products'
    )
    
    return jsonify({
        'total_stores': total_stores,
        'completed': completed,
        'failed': failed,
        'in_progress': in_progress,
        'total_products_imported': total_products,
        'success_rate': f"{(completed/total_stores*100):.1f}%" if total_stores > 0 else "0%"
    })

# ============================================================
# REST API FOR FRONTEND (MVP)
# ============================================================

def run_automation_background(store_id, user_data):
    """
    Background automation task - runs asynchronously
    Updates database with progress at each step
    """
    browser_session = None

    try:
        # Step 1: Create Shopify Account (0-25%)
        update_entry_status(store_id, {
            'current_step': 'create_account',
            'message': 'Creating your store...',
            'progress_percent': 10
        })

        from services.createStore import ShopifyAccountCreator
        account_creator = ShopifyAccountCreator()
        store_data, browser_session = account_creator.create_store(
            email=user_data['email'],
            store_name=user_data['store_name'],
            country=user_data.get('country', 'US'),
            business_type=user_data['business_type']
        )

        if not store_data or not store_data.get('store_url'):
            raise ValueError("Failed to create store: No store URL returned")

        update_entry_status(store_id, {
            'progress_percent': 25,
            'shopify_store_url': store_data.get('store_url'),
            'shopify_store_id': store_data.get('store_id')
        })

        # Step 2: Get Access Token (25-50%)
        update_entry_status(store_id, {
            'current_step': 'access_token',
            'message': 'Preparing store configuration...',
            'progress_percent': 30
        })

        from services.accessToken import AccessTokenManager
        token_manager = AccessTokenManager()
        access_token = token_manager.get_token(
            store_url=store_data['store_url'],
            driver=browser_session
        )

        if not access_token:
            raise ValueError("Failed to retrieve access token")

        # Close browser after token extraction
        if browser_session:
            try:
                browser_session.quit()
                browser_session = None
            except:
                pass

        update_entry_status(store_id, {'progress_percent': 50})

        # Step 3: Import Products (50-75%)
        update_entry_status(store_id, {
            'current_step': 'import_products',
            'message': 'Uploading products...',
            'progress_percent': 55
        })

        from services.product import ProductImporter
        product_importer = ProductImporter(access_token, store_data['store_url'])
        imported_products = product_importer.import_products(
            category=user_data.get('product_category', 'electronics'),
            count=user_data['product_count']
        )

        update_entry_status(store_id, {
            'progress_percent': 75,
            'products_imported': len(imported_products)
        })

        # Step 4: Transfer Ownership (75-99%)
        update_entry_status(store_id, {
            'current_step': 'transfer_ownership',
            'message': 'Finalizing setup and ownership transfer...',
            'progress_percent': 85
        })

        from services.transferOwner import OwnershipTransfer
        ownership_transfer = OwnershipTransfer(access_token, store_data['store_url'])
        ownership_transfer.transfer_to_customer(user_data['email'])

        # Complete!
        update_entry_status(store_id, {
            'status': 'completed',
            'current_step': 'completed',
            'message': 'Your store is ready!',
            'progress_percent': 100,
            'store_url': store_data['store_url'],
            'admin_url': store_data.get('admin_url'),
            'completed_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

        print(f"[BACKGROUND] Automation completed for store_id: {store_id}")

    except Exception as e:
        # Ensure browser is closed on error
        if browser_session:
            try:
                browser_session.quit()
            except:
                pass

        update_entry_status(store_id, {
            'status': 'failed',
            'message': 'Store creation failed',
            'error': str(e),
            'failed_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

        print(f"[BACKGROUND] Automation failed for store_id: {store_id} - {str(e)}")


@app.route('/api/stores', methods=['POST'])
def api_create_store():
    """
    REST API endpoint to start store creation
    Returns immediately with store_id for polling

    Request JSON:
    {
        "client_name": "string",
        "store_name": "string",
        "email": "string",
        "business_type": "string",
        "product_count": 5
    }

    Response (202 Accepted):
    {
        "store_id": "abc12345",
        "status": "processing",
        "message": "Store creation started"
    }
    """
    try:
        # Parse JSON input
        data = request.get_json()

        if not data:
            return jsonify({'error': 'JSON body required'}), 400

        # Validate required fields
        required_fields = ['client_name', 'store_name', 'email', 'business_type']
        for field in required_fields:
            if not data.get(field, '').strip():
                return jsonify({
                    'error': f'{field} is required',
                    'field': field
                }), 400

        # Validate email format
        email = data['email'].strip()
        if '@' not in email or '.' not in email:
            return jsonify({
                'error': 'Invalid email format',
                'field': 'email'
            }), 400

        # Validate product_count (V1: only 5 products supported)
        product_count = data.get('product_count', 5)
        if product_count != 5:
            product_count = 5  # Force to 5 in V1

        # Generate unique store_id
        store_id = generate_store_id()

        # Prepare user data
        user_data = {
            'client_name': data['client_name'].strip(),
            'email': email,
            'store_name': data['store_name'].strip(),
            'business_type': data['business_type'].strip(),
            'product_category': data.get('product_category', 'electronics'),
            'product_count': product_count,
            'country': data.get('country', 'US')
        }

        # Create initial database entry
        entry = {
            'store_id': store_id,
            'id': len(load_history()) + 1,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'user_data': user_data,
            'status': 'processing',
            'current_step': 'queued',
            'message': 'Starting store creation...',
            'progress_percent': 0,
            'steps': [],
            'store_url': None,
            'admin_url': None,
            'products_imported': 0
        }

        save_history(entry)

        # Start background automation
        executor.submit(run_automation_background, store_id, user_data)

        print(f"[API] Store creation started - store_id: {store_id}")

        # Return immediately (202 Accepted)
        return jsonify({
            'store_id': store_id,
            'status': 'processing',
            'message': 'Store creation started'
        }), 202

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/stores/<store_id>/status')
def api_get_store_status(store_id):
    """
    REST API endpoint to check store creation status
    Used for frontend polling

    Response:
    {
        "store_id": "abc12345",
        "status": "processing|completed|failed",
        "current_step": "create_account|access_token|import_products|transfer_ownership",
        "message": "Creating your store...",
        "progress_percent": 25,
        "store_url": "https://store.myshopify.com" (when completed),
        "error": "Error message" (when failed)
    }
    """
    entry = get_entry_by_store_id(store_id)

    if not entry:
        return jsonify({'error': 'Store not found'}), 404

    # Build response based on status
    response = {
        'store_id': store_id,
        'status': entry.get('status', 'processing'),
        'current_step': entry.get('current_step', 'queued'),
        'message': entry.get('message', 'Processing...'),
        'progress_percent': entry.get('progress_percent', 0),
        'created_at': entry.get('timestamp')
    }

    # Add success data when completed
    if entry.get('status') == 'completed':
        response['store_url'] = entry.get('store_url')
        response['admin_url'] = entry.get('admin_url')
        response['products_count'] = entry.get('products_imported', 0)
        response['completed_at'] = entry.get('completed_at')

    # Add error data when failed
    if entry.get('status') == 'failed':
        response['error'] = entry.get('error', 'Unknown error')
        response['failed_at'] = entry.get('failed_at')

    return jsonify(response)


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors"""
    return render_template('error.html', error="Page not found (404)"), 404

@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors"""
    return render_template('error.html', error="Internal server error (500)"), 500

# ============================================================
# MAIN ENTRY POINT
# ============================================================

if __name__ == '__main__':
    print(f"\n{'='*70}")
    print(f"SHOPIFY AUTOMATION SYSTEM")
    print(f"{'='*70}")
    
    # Validate environment variables
    try:
        validate_config()
        print("Configuration validated")
    except ValueError as e:
        print(f"Configuration Error: {str(e)}")
        print("Please create a .env file with required credentials")
        sys.exit(1)
    
    # Ensure database directory exists
    os.makedirs('database', exist_ok=True)
    if not os.path.exists(DB_PATH):
        with open(DB_PATH, 'w') as f:
            json.dump([], f)
    print("Database directory ready")
    
    print(f"Server starting on http://0.0.0.0:5000")
    print(f"{'='*70}\n")
    
    # Run the Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)