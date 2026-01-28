import requests
import json
import time
import os
import csv
import re
import hashlib
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Dict, Optional, Union, Tuple
from datetime import datetime

# ═══════════════════════════════════════════════════════════════════════
# EbayShopifyImporter - Production Version 2.0
# ═══════════════════════════════════════════════════════════════════════

class EbayShopifyImporter:
    """
    Import products from API to Shopify
    with dynamic product count, professional descriptions, and smart filtering

    Version 2.0 Changes:
    - Enhanced image extraction with deep recursive search
    - Professional minimal product descriptions (Apple-style)
    - Improved scoring algorithm with demand signals
    - CSV report generation for manual review
    """
    
    def __init__(self, shopify_store: str, access_token: str, max_products: int = 10, 
                 debug: bool = False, customer_email: str = None):
        """
        Initialize the importer
        
        Args:
            shopify_store: Shopify store URL
            access_token: Shopify access token
            max_products: Number of products to import (5-30)
            debug: Enable debug mode for image extraction
            customer_email: Customer email to send report to
        """
        self.shopify_store = shopify_store
        self.shopify_headers = {
            "X-Shopify-Access-Token": access_token,
            "Content-Type": "application/json"
        }
        self.shopify_api_version = "2024-01"
        self.shopify_url = f"https://{shopify_store}/admin/api/{self.shopify_api_version}"
        
        # Required product count (dynamic)
        self.max_products = min(max(max_products, 5), 30)  # Between 5 and 30
        
        # Debug mode
        self.debug = debug
        
        # Customer email for reports
        self.customer_email = customer_email
        
        # Email configuration (SMTP)
        # Can use Gmail, SendGrid, Mailgun, or any SMTP server
        self.email_config = {
            'smtp_server': os.environ.get('SMTP_SERVER', 'smtp.gmail.com'),
            'smtp_port': int(os.environ.get('SMTP_PORT', 587)),
            'smtp_username': os.environ.get('SMTP_USERNAME', ''),
            'smtp_password': os.environ.get('SMTP_PASSWORD', ''),  # App Password for Gmail
            'from_email': os.environ.get('FROM_EMAIL', 'noreply@yourstore.com'),
            'from_name': os.environ.get('FROM_NAME', 'Product Import System')
        }
        
        # Demand signal keywords for scoring
        self.demand_keywords = [
            'best seller', 'bestseller', 'popular', 'hot', 'trending',
            'top rated', 'top-rated', 'premium', 'professional', 'pro',
            'original', 'genuine', 'official', 'authentic', 'new arrival',
            'best quality', 'high quality', 'top quality', '5 star', '4.9'
        ]
        
        # Penalty keywords for scoring
        self.penalty_keywords = [
            'cheap', 'wholesale', 'bulk', 'lot of', 'bundle',
            'used', 'refurbished', 'replica', 'copy', 'fake',
            'unknown', 'generic', 'unbranded', 'no brand'
        ]
        
    # ═══════════════════════════════════════════════════════════════════
    # Read products from API
    # ═══════════════════════════════════════════════════════════════════

    def load_ebay_products(self, search_category: str = "phone case") -> List[Dict]:
        """Read products from API using dedicated endpoints"""

        print(f"[INFO] Fetching products from API...")
        print(f"[INFO] Search category: {search_category}")

        try:
            # Mapping from user input to dedicated endpoint + expected product_type
            endpoint_mapping = {
                # Phone Cases -> /api/products/cases
                'phone case': ('cases', 'case'),
                'phone_case': ('cases', 'case'),
                'phone cases': ('cases', 'case'),
                'phone_cases': ('cases', 'case'),
                'case': ('cases', 'case'),
                'cases': ('cases', 'case'),
                'cover': ('cases', 'case'),
                'covers': ('cases', 'case'),

                # Chargers -> /api/products/chargers
                'charger': ('chargers', 'charger'),
                'chargers': ('chargers', 'charger'),
                'cable': ('chargers', 'charger'),
                'cables': ('chargers', 'charger'),
                'adapter': ('chargers', 'charger'),
                'adapters': ('chargers', 'charger'),
                'charging': ('chargers', 'charger'),

                # Phones -> /api/products/phones
                'phone': ('phones', 'phone'),
                'phones': ('phones', 'phone'),
                'mobile': ('phones', 'phone'),
                'smartphone': ('phones', 'phone'),
                'iphone': ('phones', 'phone'),
                'samsung': ('phones', 'phone'),
                'android': ('phones', 'phone'),

                # Tablets -> /api/products/tablets
                'tablet': ('tablets', 'tablet'),
                'tablets': ('tablets', 'tablet'),
                'ipad': ('tablets', 'tablet'),

                # Audio -> /api/products/audio
                'headphones': ('audio', 'audio'),
                'headphone': ('audio', 'audio'),
                'earphones': ('audio', 'audio'),
                'earphone': ('audio', 'audio'),
                'airpods': ('audio', 'audio'),
                'airpod': ('audio', 'audio'),
                'earbuds': ('audio', 'audio'),
                'earbud': ('audio', 'audio'),
                'audio': ('audio', 'audio'),
                'buds': ('audio', 'audio'),

                # Smart Watches -> /api/products/smartwatches
                'watch': ('smartwatches', 'smartwatch'),
                'watches': ('smartwatches', 'smartwatch'),
                'smartwatch': ('smartwatches', 'smartwatch'),
                'smart watch': ('smartwatches', 'smartwatch'),
                'apple watch': ('smartwatches', 'smartwatch'),

                # Accessories -> /api/products/accessories
                'accessories': ('accessories', 'accessory'),
                'accessory': ('accessories', 'accessory'),
                'power bank': ('accessories', 'power_bank'),
                'powerbank': ('accessories', 'power_bank'),
                'screen protector': ('accessories', 'screen_protector'),

                # eBook Readers
                'ebook': ('by-type/other', None),
                'kindle': ('by-type/other', None),
                'reader': ('by-type/other', None),
            }

            # Convert category to correct endpoint
            category_lower = search_category.lower().strip()
            endpoint_info = endpoint_mapping.get(category_lower, ('accessories', None))
            api_endpoint = endpoint_info[0]
            expected_product_type = endpoint_info[1]

            # Extract keywords for filtering
            keywords_dict = self._get_search_keywords(search_category)
            keywords_dict['expected_product_type'] = expected_product_type

            print(f"[INFO] Using endpoint: /api/products/{api_endpoint}")
            print(f"[INFO] Expected product_type: {expected_product_type}")
            print(f"[INFO] Smart filtering enabled:")
            if keywords_dict.get('positive'):
                print(f"       Positive: {keywords_dict['positive'][:5]}...")
            if keywords_dict.get('required'):
                print(f"       Required: {keywords_dict['required']}")
            if keywords_dict.get('negative'):
                print(f"       Negative: {len(keywords_dict['negative'])} keywords\n")

            # Call API with dedicated endpoint
            api_url = f"http://199.192.25.89:5000/api/products/{api_endpoint}"

            print(f"[INFO] API Call: {api_url}")
            
            response = requests.get(
                api_url,
                params={'limit': 1000},
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"[ERROR] API request failed: {response.status_code}")
                
                # Fallback: try /api/products
                print(f"\n[WARN] Trying /api/products as fallback...")
                return self._fallback_load_all_products(search_category, keywords_dict)
            
            data = response.json()
            
            # Extract products from response
            all_products = []
            
            if isinstance(data, dict):
                if 'data' in data:
                    all_products = data['data']
                elif 'results' in data:
                    all_products = data['results']
                elif 'products' in data:
                    all_products = data['products']
                else:
                    # Maybe data is directly in response
                    all_products = list(data.values()) if data else []
            elif isinstance(data, list):
                all_products = data
            
            if not all_products:
                print(f"[ERROR] No products found from endpoint '{api_endpoint}'")

                # Fallback
                print(f"\n[WARN] Fetching all products...")
                return self._fallback_load_all_products(search_category, keywords_dict)

            print(f"[OK] Loaded {len(all_products)} products from '{api_endpoint}'\n")

            # Initial filtering by product_type if available
            if expected_product_type:
                filtered_by_type = [p for p in all_products if p.get('product_type') == expected_product_type]
                if filtered_by_type:
                    print(f"[OK] Filtered by product_type='{expected_product_type}': {len(filtered_by_type)} products")
                    all_products = filtered_by_type
                else:
                    print(f"[WARN] No products with product_type='{expected_product_type}', using all {len(all_products)}")
            
            # Select best products with filtering
            return self._select_best_products(all_products, keywords_dict)
            
        except requests.exceptions.Timeout:
            print("[ERROR] API request timeout")
            return []
        except requests.exceptions.ConnectionError:
            print("[ERROR] Cannot connect to API server")
            return []
        except Exception as e:
            print(f"[ERROR] {str(e)}")
            import traceback
            traceback.print_exc()
            return []

    def _get_search_keywords(self, category: str) -> dict:
        """Extract positive and negative keywords from the requested category"""

        category_lower = category.lower().strip()

        # ═══════════════════════════════════════════════════════════════════
        # Define keywords once (no duplication)
        # ═══════════════════════════════════════════════════════════════════

        # Phone Cases keywords
        PHONE_CASE_KEYWORDS = {
            'positive': [
                'phone case', 'mobile case', 'cell phone', 'smartphone case',
                # Apple
                'iphone', 'iphone 16', 'iphone 15', 'iphone 14', 'iphone 13', 'iphone 12', 'iphone 11',
                'iphone se', 'iphone pro', 'iphone plus', 'iphone max',
                # Samsung
                'samsung', 'galaxy',
                'galaxy s24', 'galaxy s23', 'galaxy s22', 'galaxy s21',
                'galaxy a54', 'galaxy a53', 'galaxy a34', 'galaxy a14',
                'galaxy note', 'galaxy z fold', 'galaxy z flip',
                # Other brands
                'xiaomi', 'redmi', 'poco', 'huawei', 'oppo', 'vivo', 'oneplus', 'pixel',
                'motorola', 'nokia', 'lg', 'sony',
            ],
            'required': ['case', 'cover'],
            'negative': [
                'watch', 'smartwatch', 'wristband', 'band strap',
                'airpod', 'earpod', 'earbuds', 'buds case', 'buds2', 'buds3',
                'earphone', 'headphone', 'headset',
                'tablet', 'ipad',
                'screen protector', 'tempered glass',
                'charger', 'charging dock', 'charging station', 'charging cable',
                'usb cable', 'power bank',
                'galaxy buds', 'airpods pro', 'airpods max',
            ]
        }

        # Charger keywords
        CHARGER_KEYWORDS = {
            'positive': ['charger', 'charging', 'adapter', 'power adapter', 'fast charger', 'usb charger'],
            'required': [],
            'negative': ['case', 'cover', 'screen protector', 'tempered glass']
        }

        # Cable keywords
        CABLE_KEYWORDS = {
            'positive': ['cable', 'cord', 'wire', 'usb-c', 'lightning', 'type-c'],
            'required': [],
            'negative': ['case', 'cover', 'screen protector']
        }

        # Audio keywords
        AUDIO_KEYWORDS = {
            'positive': ['airpods', 'airpod', 'earbuds', 'earphones', 'headphones', 'headset', 'buds', 'tws'],
            'required': [],
            'negative': ['case', 'cover', 'phone', 'tablet', 'charger only']
        }

        # Watch keywords
        WATCH_KEYWORDS = {
            'positive': ['watch', 'smartwatch', 'apple watch', 'galaxy watch', 'smart band'],
            'required': [],
            'negative': ['phone', 'case', 'tablet', 'charger']
        }

        # Phone keywords
        PHONE_KEYWORDS = {
            'positive': ['iphone', 'samsung galaxy', 'smartphone', 'mobile phone', 'android phone'],
            'required': [],
            'negative': ['case', 'cover', 'charger', 'cable', 'screen protector']
        }

        # Tablet keywords
        TABLET_KEYWORDS = {
            'positive': ['tablet', 'ipad', 'galaxy tab', 'surface'],
            'required': [],
            'negative': ['phone', 'watch', 'case', 'cover']
        }

        # Screen protector keywords
        SCREEN_PROTECTOR_KEYWORDS = {
            'positive': ['screen protector', 'tempered glass', 'glass protector', 'screen film'],
            'required': [],
            'negative': ['case', 'charger', 'cable']
        }

        # ═══════════════════════════════════════════════════════════════════
        # Category mapping (no duplication - all names point to same keywords)
        # ═══════════════════════════════════════════════════════════════════

        keyword_map = {
            # Phone Cases (all names point to same list)
            'phone case': PHONE_CASE_KEYWORDS,
            'phone_case': PHONE_CASE_KEYWORDS,
            'phone cases': PHONE_CASE_KEYWORDS,
            'phone_cases': PHONE_CASE_KEYWORDS,
            'case': PHONE_CASE_KEYWORDS,
            'cases': PHONE_CASE_KEYWORDS,
            'cover': PHONE_CASE_KEYWORDS,
            'covers': PHONE_CASE_KEYWORDS,

            # Chargers
            'charger': CHARGER_KEYWORDS,
            'chargers': CHARGER_KEYWORDS,
            'adapter': CHARGER_KEYWORDS,
            'adapters': CHARGER_KEYWORDS,

            # Cables
            'cable': CABLE_KEYWORDS,
            'cables': CABLE_KEYWORDS,

            # Audio
            'airpods': AUDIO_KEYWORDS,
            'airpod': AUDIO_KEYWORDS,
            'earbuds': AUDIO_KEYWORDS,
            'earphones': AUDIO_KEYWORDS,
            'headphones': AUDIO_KEYWORDS,
            'headphone': AUDIO_KEYWORDS,
            'audio': AUDIO_KEYWORDS,
            'buds': AUDIO_KEYWORDS,

            # Watches
            'watch': WATCH_KEYWORDS,
            'watches': WATCH_KEYWORDS,
            'smartwatch': WATCH_KEYWORDS,
            'smart watch': WATCH_KEYWORDS,
            'apple watch': WATCH_KEYWORDS,

            # Phones
            'phone': PHONE_KEYWORDS,
            'phones': PHONE_KEYWORDS,
            'iphone': PHONE_KEYWORDS,
            'samsung': PHONE_KEYWORDS,
            'mobile': PHONE_KEYWORDS,
            'smartphone': PHONE_KEYWORDS,

            # Tablets
            'tablet': TABLET_KEYWORDS,
            'tablets': TABLET_KEYWORDS,
            'ipad': TABLET_KEYWORDS,

            # Screen Protectors
            'screen protector': SCREEN_PROTECTOR_KEYWORDS,
            'screen protectors': SCREEN_PROTECTOR_KEYWORDS,
            'tempered glass': SCREEN_PROTECTOR_KEYWORDS,
        }

        # If found in the map
        if category_lower in keyword_map:
            return keyword_map[category_lower].copy()

        # Otherwise use words from category itself
        words = category_lower.replace('_', ' ').split()
        positive = [w for w in words if len(w) > 2]
        return {
            'positive': positive,
            'required': [],
            'negative': []
        }

    def _fallback_load_all_products(self, search_category: str, keywords_dict: dict) -> List[Dict]:
        """Fallback plan: fetch all products and filter locally"""
        
        try:
            api_url = "http://199.192.25.89:5000/api/products"
            
            response = requests.get(
                api_url,
                params={'limit': 1000},
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"[ERROR] /api/products also failed: {response.status_code}")
                return []
            
            data = response.json()
            
            all_products = []
            
            if isinstance(data, dict):
                if 'data' in data:
                    all_products = data['data']
                elif 'results' in data:
                    all_products = data['results']
                elif 'products' in data:
                    all_products = data['products']
            elif isinstance(data, list):
                all_products = data
            
            if not all_products:
                print(f"[ERROR] No products in /api/products")
                return []
            
            print(f"[OK] Found {len(all_products)} products from /api/products")
            
            # Local filtering
            filtered = self._filter_by_keywords(all_products, keywords_dict)

            if filtered:
                print(f"[OK] After filtering: {len(filtered)} matching products")
                return self._select_best_products(filtered, keywords_dict)
            else:
                print(f"[WARN] No matching products found, using random sample")
                # Take random sample
                import random
                sample = random.sample(all_products, min(50, len(all_products)))
                return self._select_best_products(sample, keywords_dict)
        
        except Exception as e:
            print(f"[ERROR] Fallback error: {str(e)}")
            return []

    # ═══════════════════════════════════════════════════════════════════
    # Enhanced Image API Integration
    # ═══════════════════════════════════════════════════════════════════

    def _request_enhanced_images(self, item_ids: List[str]) -> Dict:
        """
        Request enhanced images for products from server API

        Args:
            item_ids: List of item_ids to enhance

        Returns:
            Dict: API response with enhancement results
        """
        api_url = "http://199.192.25.89:5000/api/enhance"

        payload = {
            "product_ids": item_ids,
            "force_redownload": False
        }

        try:
            response = requests.post(api_url, json=payload, timeout=300)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"[ERROR] Failed to enhance images: {e}")

        return {"success": False, "data": {}}

    def _get_enhanced_product_images(self, item_id: str) -> List[str]:
        """
        Fetch enhanced images for a single product from API

        Args:
            item_id: Product identifier

        Returns:
            List[str]: List of enhanced image URLs
        """
        api_url = f"http://199.192.25.89:5000/api/enhanced/{item_id}"

        try:
            # Reduced timeout from 30s to 5s (this function should rarely be called now)
            response = requests.get(api_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('data', {}).get('enhanced'):
                    images_data = data['data'].get('images', [])
                    # Extract URLs from images
                    return [img['url'] for img in images_data if 'url' in img]
        except Exception as e:
            if self.debug:
                print(f"[WARN] Could not fetch enhanced images for {item_id}: {e}")

        return []

    def _enhance_products_batch(self, products: List[Dict]) -> None:
        """
        Enhance a batch of products at once

        Args:
            products: List of products to enhance
        """
        # Extract item_ids
        item_ids = []

        # Debug: print first product to verify structure
        if products and self.debug:
            print(f"[DEBUG] First product keys: {list(products[0].keys())}")
            print(f"[DEBUG] item_id value: {products[0].get('item_id')}")

        for p in products:
            item_id = p.get('item_id') or p.get('id') or p.get('itemId')
            if item_id:
                item_ids.append(str(item_id))

        if not item_ids:
            print("[WARN] No valid item_ids found for enhancement")
            if products:
                print(f"[DEBUG] Sample product keys: {list(products[0].keys())[:10]}")
                print(f"[DEBUG] Sample product: {str(products[0])[:200]}")
            return

        print(f"[DEBUG] Sending {len(item_ids)} item_ids to server: {item_ids[:3]}...")

        print(f"\n[INFO] Requesting enhanced images for {len(item_ids)} products...")
        print(f"[INFO] Sending request to: http://199.192.25.89:5000/api/enhance")

        # Request enhancement in batch
        result = self._request_enhanced_images(item_ids)

        if result.get('success'):
            data = result.get('data', {})
            success_count = len(data.get('success', []))
            failed_count = len(data.get('failed', []))
            total_images = data.get('total_images', 0)
            processing_time = data.get('processing_time', 0)

            print(f"[SUCCESS] Enhanced {success_count} products")
            print(f"[INFO] Total images: {total_images}")
            print(f"[INFO] Processing time: {processing_time:.1f}s")

            if failed_count > 0:
                print(f"[WARN] Failed: {failed_count} products")
        else:
            print("[ERROR] Image enhancement request failed")

    # ═══════════════════════════════════════════════════════════════════
    # Product Filtering and Selection
    # ═══════════════════════════════════════════════════════════════════

    def _filter_by_keywords(self, products: List[Dict], keywords_dict: dict, strict_mode: bool = True) -> List[Dict]:
        """
        Filter products by keywords - enhanced version

        Args:
            products: List of products
            keywords_dict: Keywords dictionary (positive, required, negative, expected_product_type)
            strict_mode: If True, filter by TITLE only (more accurate). If False, filter by all text.

        Returns:
            Filtered products list
        """

        positive = keywords_dict.get('positive', [])
        required = keywords_dict.get('required', [])
        negative = keywords_dict.get('negative', [])
        expected_type = keywords_dict.get('expected_product_type')

        if not positive and not required and not negative and not expected_type:
            return products

        filtered = []
        rejected_reasons = {'negative': 0, 'required': 0, 'positive': 0, 'type': 0}

        for product in products:
            title = product.get('title', product.get('name', '')).lower()
            description = product.get('description', '').lower()
            product_type = product.get('product_type', '').lower()

            # In strict_mode check title only, otherwise check all text
            check_text = title if strict_mode else f"{title} {description}"

            # ═══════════════════════════════════════════════════════════════
            # 1. Filter by product_type (first and most important filter)
            # ═══════════════════════════════════════════════════════════════
            if expected_type and product_type:
                if product_type != expected_type:
                    rejected_reasons['type'] += 1
                    continue

            # ═══════════════════════════════════════════════════════════════
            # 2. Exclude products containing negative keywords in TITLE
            # ═══════════════════════════════════════════════════════════════
            skip = False
            for neg_word in negative:
                if neg_word.lower() in title:  # Always check title for negative
                    skip = True
                    break

            if skip:
                rejected_reasons['negative'] += 1
                continue

            # ═══════════════════════════════════════════════════════════════
            # 3. Check required keywords (must have one of them in TITLE)
            # ═══════════════════════════════════════════════════════════════
            if required:
                has_required = any(req.lower() in title for req in required)
                if not has_required:
                    rejected_reasons['required'] += 1
                    continue

            # ═══════════════════════════════════════════════════════════════
            # 4. Check positive keywords
            # ═══════════════════════════════════════════════════════════════
            if positive:
                has_positive = any(pos.lower() in check_text for pos in positive)
                if not has_positive:
                    rejected_reasons['positive'] += 1
                    continue

            filtered.append(product)

        # Print filtering summary
        total_rejected = sum(rejected_reasons.values())
        if total_rejected > 0:
            print(f"[FILTER] Rejected {total_rejected} products:")
            if rejected_reasons['type'] > 0:
                print(f"         - Wrong product_type: {rejected_reasons['type']}")
            if rejected_reasons['negative'] > 0:
                print(f"         - Negative keywords: {rejected_reasons['negative']}")
            if rejected_reasons['required'] > 0:
                print(f"         - Missing required: {rejected_reasons['required']}")
            if rejected_reasons['positive'] > 0:
                print(f"         - No positive match: {rejected_reasons['positive']}")

        return filtered
    
    def _select_best_products(self, products: List[Dict], keywords_dict: dict = None) -> List[Dict]:
        """Select best products by required count with smart filtering and scoring"""

        print(f"\n[INFO] Analyzing {len(products)} products to select best {self.max_products}...")

        # ═══════════════════════════════════════════════════════════════════
        # Filter products using enhanced function (no code duplication)
        # ═══════════════════════════════════════════════════════════════════
        if keywords_dict:
            filtered_products = self._filter_by_keywords(products, keywords_dict, strict_mode=True)
            print(f"[OK] After filtering: {len(filtered_products)} matching products")

            if len(filtered_products) >= self.max_products:
                products = filtered_products
            elif len(filtered_products) > 0:
                print(f"[WARN] Only {len(filtered_products)} matching products")
                products = filtered_products
            else:
                print(f"[WARN] No matching products!")
                return []

        scored_products = []

        # Progress indicator for scoring phase
        print(f"[INFO] Scoring {len(products)} products...")
        progress_interval = max(1, len(products) // 10)

        for idx, product in enumerate(products):
            # Show progress every 10%
            if (idx + 1) % progress_interval == 0:
                print(f"  Progress: {idx + 1}/{len(products)} ({((idx+1)/len(products)*100):.0f}%)")

            title = product.get('title', product.get('name', ''))
            price = self._extract_price(product)
            # Use scoring_mode=True to skip slow HTTP fetching
            images = self._extract_images(product, scoring_mode=True)
            
            if not title or not price or not images:
                continue
            
            # Calculate enhanced score
            score, score_breakdown = self._calculate_product_score_v2(product, price, images, keywords_dict)
            
            scored_products.append({
                'product': product,
                'index': idx,
                'score': score,
                'score_breakdown': score_breakdown,
                'title': title,
                'price': price,
                'images': images
            })
        
        # Sort by score
        scored_products.sort(key=lambda x: x['score'], reverse=True)
        selected = scored_products[:self.max_products]

        # ═══════════════════════════════════════════════════════════════
        # Download enhanced images ONLY for selected products
        # ═══════════════════════════════════════════════════════════════
        print(f"\n[INFO] Downloading enhanced images for {len(selected)} selected products...")
        selected_products_list = [item['product'] for item in selected]
        self._enhance_products_batch(selected_products_list)

        # Re-extract images after enhancement
        for item in selected:
            item['images'] = self._extract_images(item['product'])

        print(f"\n{'='*70}")
        print(f"TOP {len(selected)} PRODUCTS (Ranked by Score)")
        print(f"{'='*70}")
        
        for i, item in enumerate(selected, 1):
            print(f"{i}. {item['title'][:55]}...")
            print(f"   Price: ${item['price']:.2f} | Score: {item['score']:.0f} | Images: {len(item['images'])}")
            breakdown = item['score_breakdown']
            print(f"   [Base:{breakdown['base']:.0f} Price:{breakdown['price']:.0f} Images:{breakdown['images']:.0f} Demand:{breakdown['demand']:.0f} Quality:{breakdown['quality']:.0f}]")
        
        print(f"{'='*70}\n")
        
        # Convert to final format
        final_products = []
        for item in selected:
            parsed = self._parse_product(item)
            if parsed:
                parsed['final_score'] = item['score']
                parsed['score_breakdown'] = item['score_breakdown']
                final_products.append(parsed)
        
        return final_products
    
    def _calculate_product_score_v2(self, product: Dict, price: float, images: List[str], keywords_dict: dict = None) -> Tuple[float, Dict]:
        """
        Calculate enhanced product score with multiple criteria
        
        Scoring Weights:
        - Base Score: 50 points
        - Price Score: 0-25 points (optimal range $15-$60)
        - Image Score: 0-30 points (based on count and quality)
        - Demand Signals: 0-40 points
        - Quality Signals: 0-25 points
        - Penalties: -10 to -50 points
        
        Max Possible: ~170 points
        """
        
        score = 50  # Base score
        breakdown = {
            'base': 50,
            'price': 0,
            'images': 0,
            'demand': 0,
            'quality': 0,
            'penalty': 0
        }
        
        title = product.get('title', product.get('name', '')).lower()
        description = product.get('description', '').lower()
        text = f"{title} {description}"
        
        # ═══════════════════════════════════════════════════════════════
        # 1. PRICE SCORE (0-25 points)
        # ═══════════════════════════════════════════════════════════════
        original_price = price / 1.4  # Get original before markup
        
        if 15 <= price <= 60:
            # Sweet spot for dropshipping
            breakdown['price'] = 25
        elif 10 <= price < 15 or 60 < price <= 80:
            breakdown['price'] = 18
        elif 5 <= price < 10 or 80 < price <= 100:
            breakdown['price'] = 10
        elif price > 100:
            breakdown['price'] = 5
        else:
            # Very cheap items (likely low quality)
            breakdown['price'] = 0
        
        # Profit margin bonus
        profit_margin = ((price - original_price) / original_price) * 100
        if profit_margin >= 50:
            breakdown['price'] += 5
        elif profit_margin >= 40:
            breakdown['price'] += 3
        
        score += breakdown['price']
        
        # ═══════════════════════════════════════════════════════════════
        # 2. IMAGE SCORE (0-30 points)
        # ═══════════════════════════════════════════════════════════════
        image_count = len(images)
        
        if image_count >= 6:
            breakdown['images'] = 30
        elif image_count >= 4:
            breakdown['images'] = 25
        elif image_count >= 3:
            breakdown['images'] = 20
        elif image_count >= 2:
            breakdown['images'] = 12
        elif image_count >= 1:
            breakdown['images'] = 5
        else:
            breakdown['images'] = 0
        
        # Bonus for high-quality eBay images
        for img in images:
            if 's-l1600' in img or 's-l1200' in img:
                breakdown['images'] += 2
                break
        
        score += breakdown['images']
        
        # ═══════════════════════════════════════════════════════════════
        # 3. DEMAND SIGNALS (0-40 points)
        # ═══════════════════════════════════════════════════════════════
        demand_score = 0
        
        for keyword in self.demand_keywords:
            if keyword in text:
                demand_score += 8
                if demand_score >= 40:
                    break
        
        # Seller rating bonus
        seller_rating = product.get('seller_rating', product.get('rating', None))
        if seller_rating:
            try:
                rating = float(str(seller_rating).replace('%', '').replace('+', ''))
                if rating >= 99:
                    demand_score += 10
                elif rating >= 98:
                    demand_score += 7
                elif rating >= 95:
                    demand_score += 4
            except:
                pass
        
        # Product rating bonus
        product_rating = product.get('product_rating', product.get('stars', None))
        if product_rating:
            try:
                rating = float(str(product_rating))
                if rating >= 4.8:
                    demand_score += 8
                elif rating >= 4.5:
                    demand_score += 5
                elif rating >= 4.0:
                    demand_score += 2
            except:
                pass
        
        breakdown['demand'] = min(demand_score, 40)
        score += breakdown['demand']
        
        # ═══════════════════════════════════════════════════════════════
        # 4. QUALITY SIGNALS (0-25 points)
        # ═══════════════════════════════════════════════════════════════
        quality_score = 0
        
        # Title quality
        title_length = len(title)
        if 30 <= title_length <= 120:
            quality_score += 8
        elif 20 <= title_length < 30 or 120 < title_length <= 150:
            quality_score += 4
        
        # Description quality
        desc_length = len(description)
        if desc_length > 200:
            quality_score += 7
        elif desc_length > 100:
            quality_score += 4
        elif desc_length > 50:
            quality_score += 2
        
        # Brand mentions
        premium_brands = ['apple', 'samsung', 'sony', 'bose', 'anker', 'spigen', 'otterbox', 'belkin']
        for brand in premium_brands:
            if brand in text:
                quality_score += 5
                break
        
        # Keyword match bonus (if keywords provided)
        if keywords_dict:
            positive = keywords_dict.get('positive', [])
            for keyword in positive[:5]:
                if keyword.lower() in title:
                    quality_score += 3
                    break
        
        breakdown['quality'] = min(quality_score, 25)
        score += breakdown['quality']
        
        # ═══════════════════════════════════════════════════════════════
        # 5. PENALTIES (-10 to -50 points)
        # ═══════════════════════════════════════════════════════════════
        penalty = 0
        
        for keyword in self.penalty_keywords:
            if keyword in text:
                penalty += 10
                if penalty >= 50:
                    break
        
        # Very short title penalty
        if len(title) < 15:
            penalty += 10
        
        # No description penalty
        if len(description) < 20:
            penalty += 8
        
        # Single image penalty
        if image_count == 1:
            penalty += 5
        
        breakdown['penalty'] = -min(penalty, 50)
        score += breakdown['penalty']
        
        return max(score, 0), breakdown
    
    # ═══════════════════════════════════════════════════════════════════
    # Extract data from product - ENHANCED IMAGE EXTRACTION
    # ═══════════════════════════════════════════════════════════════════

    def _extract_price(self, product: Dict) -> Optional[float]:
        """Extract price from product"""

        # Try to get price from different fields
        price_fields = ['price', 'current_price', 'selling_price', 'sale_price', 
                       'ebay_price', 'cost', 'amount']
        
        for field in price_fields:
            if field in product:
                price = self._clean_price_value(product[field])
                if price and price > 0:
                    # Add markup for profit (40%)
                    return round(price * 1.4, 2)

        # Default price
        return 19.99
    
    def _fetch_images_from_url(self, url: str) -> List[str]:
        """
        Fetch product images directly from the product page URL
        
        This function makes a GET request to the product page and extracts
        all high-quality image URLs using regex patterns.
        
        Args:
            url: Product page URL (eBay, AliExpress, etc.)
        
        Returns:
            List of unique high-resolution image URLs
        """
        if not url or not url.startswith('http'):
            return []
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
            }
            
            if self.debug:
                print(f"[DEBUG] Fetching images from URL: {url[:60]}...")
            
            response = requests.get(url, timeout=15, headers=headers)
            
            if response.status_code != 200:
                if self.debug:
                    print(f"[DEBUG] URL fetch failed with status: {response.status_code}")
                return []
            
            html_content = response.text
            found_images = []
            
            # Pattern 1: eBay high-quality images (s-l1600)
            ebay_pattern_1600 = r'https?://i\.ebayimg\.com/images/g/[A-Za-z0-9~_-]+/s-l1600\.(?:jpg|jpeg|png|webp)'
            found_1600 = re.findall(ebay_pattern_1600, html_content, re.IGNORECASE)
            found_images.extend(found_1600)
            
            # Pattern 2: eBay medium-quality images (upgrade later)
            ebay_pattern_other = r'https?://i\.ebayimg\.com/images/g/[A-Za-z0-9~_-]+/s-l\d+\.(?:jpg|jpeg|png|webp)'
            found_other = re.findall(ebay_pattern_other, html_content, re.IGNORECASE)
            found_images.extend(found_other)
            
            # Pattern 3: eBay thumbs format
            ebay_thumbs_pattern = r'https?://i\.ebayimg\.com/thumbs/images/g/[A-Za-z0-9~_-]+/s-l\d+\.(?:jpg|jpeg|png|webp)'
            found_thumbs = re.findall(ebay_thumbs_pattern, html_content, re.IGNORECASE)
            found_images.extend(found_thumbs)
            
            # Pattern 4: eBay d/ format images
            ebay_d_pattern = r'https?://i\.ebayimg\.com/d/[A-Za-z0-9/_-]+\.(?:jpg|jpeg|png|webp)'
            found_d = re.findall(ebay_d_pattern, html_content, re.IGNORECASE)
            found_images.extend(found_d)
            
            # Pattern 5: AliExpress images
            ali_pattern = r'https?://[a-z0-9-]+\.alicdn\.com/[^\s\'"<>]+\.(?:jpg|jpeg|png|webp)'
            found_ali = re.findall(ali_pattern, html_content, re.IGNORECASE)
            found_images.extend(found_ali)
            
            # Pattern 6: Generic high-res image pattern in JSON data
            json_img_pattern = r'"(?:image|img|picture|photo)(?:Url|URL|_url|Src)?"\s*:\s*"(https?://[^"]+\.(?:jpg|jpeg|png|webp))"'
            found_json = re.findall(json_img_pattern, html_content, re.IGNORECASE)
            found_images.extend(found_json)
            
            # Pattern 7: Image URLs in data attributes
            data_attr_pattern = r'data-(?:src|zoom|image|original)\s*=\s*["\']?(https?://[^\s\'"<>]+\.(?:jpg|jpeg|png|webp))["\']?'
            found_data = re.findall(data_attr_pattern, html_content, re.IGNORECASE)
            found_images.extend(found_data)
            
            # Deduplicate and upgrade to high resolution
            unique_images = []
            seen_normalized = set()
            
            for img in found_images:
                # Clean the URL
                img = self._clean_image_url(img)
                if not img:
                    continue
                
                # Upgrade to high resolution
                img = self._upgrade_to_high_res(img)
                
                # Normalize for deduplication
                normalized = self._normalize_url_for_dedup(img)
                if normalized in seen_normalized:
                    continue
                seen_normalized.add(normalized)
                
                # Validate
                if self._is_valid_image_url(img):
                    unique_images.append(img)
            
            if self.debug:
                print(f"[DEBUG] Fetched {len(unique_images)} unique images from URL")
            
            return unique_images[:20]  # Limit to 20 images max
            
        except requests.exceptions.Timeout:
            if self.debug:
                print(f"[DEBUG] URL fetch timeout: {url[:50]}")
            return []
        except requests.exceptions.RequestException as e:
            if self.debug:
                print(f"[DEBUG] URL fetch request error: {str(e)[:50]}")
            return []
        except Exception as e:
            if self.debug:
                print(f"[DEBUG] URL fetch error: {str(e)[:50]}")
            return []

    def _extract_images(self, product: Dict, scoring_mode: bool = False) -> List[str]:
        """
        Enhanced image extraction with API support and deep recursive search

        Args:
            product: Product dictionary
            scoring_mode: If True, skip slow HTTP fetching (for scoring 605 products fast)

        Features:
        - API-enhanced images from server (NEW)
        - Deep recursive object traversal
        - Multiple URL pattern detection
        - eBay URL resolution to highest quality
        - Smart deduplication
        - Direct URL fetching for missing images
        - No fabrication of images
        """

        images = set()  # Use set for automatic deduplication
        debug = self.debug

        if debug:
            print(f"\n[DEBUG] Extracting images from: {product.get('title', 'Unknown')[:50]}")

        # ═══════════════════════════════════════════════════════════════
        # STEP 0: Try to get enhanced images from API FIRST
        # ═══════════════════════════════════════════════════════════════
        # DISABLED: Individual API calls removed - batch processing is done
        # in _select_best_products() before scoring loop to avoid 605 sequential
        # HTTP requests. This reduces processing time from 10-20 minutes to <2 minutes.
        #
        # item_id = product.get('item_id') or product.get('id') or product.get('itemId')
        #
        # if item_id:
        #     enhanced_images = self._get_enhanced_product_images(str(item_id))
        #     if enhanced_images:
        #         if debug:
        #             print(f"[DEBUG] Found {len(enhanced_images)} enhanced images from API")
        #         images.update(enhanced_images)
        #
        #         # If we got 5+ enhanced images, use them directly
        #         if len(enhanced_images) >= 5:
        #             return self._sort_by_quality(list(images))

        # ═══════════════════════════════════════════════════════════════
        # STEP 1: Direct field extraction
        # ═══════════════════════════════════════════════════════════════
        image_fields = [
            'images', 'image', 'image_url', 'imageUrl', 'imageUrls', 'image_urls',
            'picture', 'pictures', 'photo', 'photos', 'thumbnail', 'thumbnails',
            'gallery', 'galleryURL', 'gallery_url', 'galleryUrls', 'pictureURLs',
            'img', 'imgs', 'pic', 'pics', 'media', 'mediaUrls',
            'pictureURL', 'PictureURL', 'galleryPictureURL', 'GalleryURL',
            'src', 'image_src', 'image_sources', 'urls', 'links', 'image_links',
            'main_image', 'mainImage', 'primary_image', 'primaryImage',
            'additional_images', 'additionalImages', 'extra_images'
        ]
        
        for field in image_fields:
            if field not in product:
                continue
            
            img_data = product[field]
            extracted = self._extract_from_value(img_data, debug, f"field:{field}")
            images.update(extracted)
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 2: Deep recursive search in all nested objects
        # ═══════════════════════════════════════════════════════════════
        deep_images = self._deep_extract_images(product, visited=set(), depth=0, max_depth=5)
        images.update(deep_images)
        
        if debug:
            print(f"[DEBUG] After deep search: {len(images)} images")
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 3: Regex fallback - find URLs in stringified data
        # ═══════════════════════════════════════════════════════════════
        if len(images) < 3:
            url_patterns = [
                r'https?://[^\s\'"<>\]]+\.(?:jpg|jpeg|png|gif|webp)(?:\?[^\s\'"<>\]]*)?',
                r'https?://i\.ebayimg\.com/[^\s\'"<>\]]+',
                r'https?://[^\s\'"<>\]]*ebayimg[^\s\'"<>\]]+',
            ]
            
            try:
                product_str = json.dumps(product)
                for pattern in url_patterns:
                    found_urls = re.findall(pattern, product_str, re.IGNORECASE)
                    for url in found_urls:
                        cleaned = self._clean_image_url(url)
                        if cleaned and self._is_valid_image_url(cleaned):
                            images.add(cleaned)
                            if debug:
                                print(f"[DEBUG] Regex found: {cleaned[:60]}")
            except:
                pass
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 4: Clean, validate, and optimize URLs
        # ═══════════════════════════════════════════════════════════════
        valid_images = []
        seen_normalized = set()
        
        for img in images:
            if not img or len(img) < 10:
                continue
            
            # Upgrade to high resolution
            img = self._upgrade_to_high_res(img)
            
            # Normalize for deduplication
            normalized = self._normalize_url_for_dedup(img)
            if normalized in seen_normalized:
                continue
            seen_normalized.add(normalized)
            
            # Validate URL structure
            if self._is_valid_image_url(img):
                valid_images.append(img)
        
        if debug:
            print(f"[DEBUG] Final validated: {len(valid_images)} images")
        
        # Sort by quality indicators
        valid_images = self._sort_by_quality(valid_images)
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 5: Fetch from URL if insufficient images
        # SKIP during scoring_mode - too slow for 605 products (15s × 605 = hours!)
        # ═══════════════════════════════════════════════════════════════
        if len(valid_images) < 3 and not scoring_mode:
            # Try to get product URL
            product_url = None
            url_fields = ['url', 'link', 'product_url', 'productUrl', 'itemUrl', 
                         'item_url', 'href', 'viewItemURL', 'ebay_url', 'source_url']
            
            for field in url_fields:
                if field in product and isinstance(product[field], str):
                    potential_url = product[field].strip()
                    if potential_url.startswith('http'):
                        product_url = potential_url
                        break
            
            # Also check nested objects for URL
            if not product_url:
                for key, value in product.items():
                    if isinstance(value, dict):
                        for url_field in url_fields:
                            if url_field in value and isinstance(value[url_field], str):
                                potential_url = value[url_field].strip()
                                if potential_url.startswith('http'):
                                    product_url = potential_url
                                    break
                    if product_url:
                        break
            
            if product_url:
                if debug:
                    print(f"[DEBUG] Fetching additional images from product URL...")
                
                # Fetch images from the product page
                fetched_images = self._fetch_images_from_url(product_url)
                
                if fetched_images:
                    if debug:
                        print(f"[DEBUG] Got {len(fetched_images)} images from URL")
                    
                    # Merge with existing images, avoiding duplicates
                    existing_normalized = {self._normalize_url_for_dedup(img) for img in valid_images}
                    
                    for img in fetched_images:
                        normalized = self._normalize_url_for_dedup(img)
                        if normalized not in existing_normalized:
                            valid_images.append(img)
                            existing_normalized.add(normalized)
                    
                    # Re-sort by quality after adding new images
                    valid_images = self._sort_by_quality(valid_images)
                    
                    if debug:
                        print(f"[DEBUG] Total images after URL fetch: {len(valid_images)}")
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 6: Final validation and return
        # ═══════════════════════════════════════════════════════════════
        
        if debug:
            print(f"[DEBUG] Final image count: {len(valid_images)}")
        
        # Return 3-10 images, or placeholder if none
        if not valid_images:
            return ['https://via.placeholder.com/800x800/f5f5f5/333333?text=Image+Not+Available']
        
        return valid_images[:10]
    
    def _extract_from_value(self, value, debug: bool = False, source: str = "") -> set:
        """Extract image URLs from any value type"""
        
        results = set()
        
        if value is None:
            return results
        
        # String: single URL
        if isinstance(value, str):
            cleaned = self._clean_image_url(value.strip())
            if cleaned and self._is_valid_image_url(cleaned):
                results.add(cleaned)
                if debug:
                    print(f"[DEBUG] {source} string: {cleaned[:60]}")
        
        # List: multiple items
        elif isinstance(value, list):
            for item in value:
                results.update(self._extract_from_value(item, debug, f"{source}[list]"))
        
        # Dict: extract from values
        elif isinstance(value, dict):
            # Check common keys first
            for key in ['url', 'src', 'href', 'link', 'imageUrl', 'image_url', 'URL', 'source']:
                if key in value:
                    results.update(self._extract_from_value(value[key], debug, f"{source}[{key}]"))
            
            # Then check all values
            for k, v in value.items():
                if any(word in k.lower() for word in ['image', 'img', 'photo', 'picture', 'url', 'src']):
                    results.update(self._extract_from_value(v, debug, f"{source}[{k}]"))
        
        return results
    
    def _deep_extract_images(self, obj, visited: set, depth: int, max_depth: int) -> set:
        """Recursively extract all image URLs from nested structures"""
        
        results = set()
        
        if depth >= max_depth:
            return results
        
        # Avoid circular references
        obj_id = id(obj)
        if obj_id in visited:
            return results
        visited.add(obj_id)
        
        if isinstance(obj, str):
            cleaned = self._clean_image_url(obj.strip())
            if cleaned and self._is_valid_image_url(cleaned):
                results.add(cleaned)
        
        elif isinstance(obj, list):
            for item in obj:
                results.update(self._deep_extract_images(item, visited, depth + 1, max_depth))
        
        elif isinstance(obj, dict):
            for key, value in obj.items():
                # Check if key suggests image content
                if any(word in key.lower() for word in ['image', 'img', 'photo', 'picture', 'gallery', 'pic', 'media', 'thumb']):
                    results.update(self._extract_from_value(value, self.debug, f"deep:{key}"))
                
                # Recurse into nested objects
                results.update(self._deep_extract_images(value, visited, depth + 1, max_depth))
        
        return results
    
    def _is_valid_image_url(self, url: str) -> bool:
        """
        Validate that a URL is likely a valid image URL
        
        Checks:
        - URL structure and length
        - HTTP/HTTPS protocol
        - Image extension or known image host
        - Excludes tracking pixels and icons
        """
        
        if not url or len(url) < 15:
            return False
        
        if not url.startswith(('http://', 'https://')):
            return False
        
        url_lower = url.lower()
        
        # Exclude tracking pixels, icons, and small images
        exclusion_patterns = [
            'pixel', 'tracking', 'beacon', 'spacer', 'blank',
            '1x1', '1px', 'transparent', 'icon', 'favicon',
            'logo', 'badge', 'button', 'sprite', 'loading',
            'placeholder', 'spinner', 'ajax', 'analytics'
        ]
        
        for pattern in exclusion_patterns:
            if pattern in url_lower:
                return False
        
        # Check for image extensions or known image hosts
        image_indicators = [
            # Extensions
            '.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff',
            # eBay
            'ebayimg.com', 'ebaystatic.com',
            # AliExpress / Alibaba
            'alicdn.com', 'aliexpress.com/item_pic',
            # Amazon
            'images-amazon.com', 'ssl-images-amazon.com', 'm.media-amazon.com',
            # Shopify
            'cdn.shopify.com', 'shopify.com/s/files',
            # Cloud services
            'cloudinary.com', 'imgix.net', 'cloudfront.net',
            # Image hosting
            'i.imgur.com', 'images.unsplash.com',
            # Generic patterns
            '/images/', '/img/', '/photos/', '/pictures/', '/gallery/',
            'image.', 'img.', 'photo.', 'pic.',
            # E-commerce patterns
            '/product-images/', '/product_images/', '/product/',
            'etsystatic.com', 'wixmp.com'
        ]
        
        has_indicator = any(indicator in url_lower for indicator in image_indicators)
        
        if not has_indicator:
            return False
        
        # Additional validation: URL shouldn't be too long (likely malformed)
        if len(url) > 2000:
            return False
        
        return True
    
    def _verify_image_accessible(self, url: str, timeout: int = 5) -> bool:
        """
        Verify that an image URL is actually accessible
        
        Makes a HEAD request to check if the image exists and is valid.
        Only use this for critical validation as it adds network overhead.
        
        Args:
            url: Image URL to verify
            timeout: Request timeout in seconds
        
        Returns:
            True if image is accessible, False otherwise
        """
        if not url or not url.startswith('http'):
            return False
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.head(url, timeout=timeout, headers=headers, allow_redirects=True)
            
            if response.status_code == 200:
                # Check content type
                content_type = response.headers.get('Content-Type', '').lower()
                if 'image' in content_type:
                    return True
                
                # Some servers don't return proper content-type for HEAD
                # Check by extension as fallback
                if any(url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                    return True
            
            return False
            
        except Exception:
            return False
    
    def _normalize_url_for_dedup(self, url: str) -> str:
        """Normalize URL for deduplication comparison"""
        
        # Remove size parameters for comparison
        normalized = url.lower()
        
        # eBay: remove size indicators
        normalized = re.sub(r's-l\d+', 's-l', normalized)
        normalized = re.sub(r'\$_\d+', '$_', normalized)
        
        # Remove query parameters
        if '?' in normalized:
            normalized = normalized.split('?')[0]
        
        return normalized
    
    def _upgrade_to_high_res(self, url: str) -> str:
        """
        Upgrade image URL to highest available resolution
        
        Supports:
        - eBay image size upgrade (s-lXXX -> s-l1600)
        - eBay thumbnail upgrade ($_X -> $_57)
        - AliExpress image size upgrade
        - Generic size parameter removal
        """
        if not url:
            return url
        
        # ═══════════════════════════════════════════════════════════════
        # eBay Image Upgrades
        # ═══════════════════════════════════════════════════════════════
        if 'ebayimg.com' in url:
            # Upgrade s-lXXX sizes to s-l1600
            size_patterns = [
                'e-l64', 's-l64', 's-l96', 's-l140', 's-l225', 's-l300', 
                's-l400', 's-l500', 's-l800', 's-l1200'
            ]
            for pattern in size_patterns:
                if pattern in url:
                    url = url.replace(pattern, 's-l1600')
                    break
            
            # Convert thumbs URL to regular URL
            if '/thumbs/images/' in url:
                url = url.replace('/thumbs/images/', '/images/')
            
            # Upgrade $_X thumbnails to $_57 (large)
            # $_0, $_1, $_2, ... $_99 -> $_57
            url = re.sub(r'\$_\d+\.', '$_57.', url)
            
            # Also handle $_XX patterns like $_T2, $_12, etc.
            url = re.sub(r'\$_[A-Z0-9]+\.', '$_57.', url)
            
            # Ensure we have the right extension
            if not any(url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']):
                # Try to extract and fix extension
                ext_match = re.search(r'\.(jpg|jpeg|png|webp|gif)', url, re.IGNORECASE)
                if ext_match:
                    # URL might have extra stuff after extension, clean it
                    ext_pos = ext_match.end()
                    url = url[:ext_pos]
        
        # ═══════════════════════════════════════════════════════════════
        # AliExpress Image Upgrades
        # ═══════════════════════════════════════════════════════════════
        elif 'alicdn.com' in url or 'aliexpress' in url:
            # Remove size suffixes like _50x50, _100x100, etc.
            url = re.sub(r'_\d+x\d+\.', '.', url)
            # Remove quality parameters
            url = re.sub(r'\.jpg_\d+x\d+\.jpg', '.jpg', url)
            # Remove webp conversion parameters
            url = re.sub(r'\.jpg\.webp$', '.jpg', url)
            url = re.sub(r'_Q\d+\.jpg', '.jpg', url)
        
        # ═══════════════════════════════════════════════════════════════
        # Amazon Image Upgrades
        # ═══════════════════════════════════════════════════════════════
        elif 'amazon' in url or 'ssl-images-amazon' in url:
            # Remove size restrictions like ._SX300_ or ._SL500_
            url = re.sub(r'\._[A-Z]{2}\d+_\.', '.', url)
            url = re.sub(r'\._[A-Z]+_\.', '.', url)
        
        # ═══════════════════════════════════════════════════════════════
        # Shopify CDN Image Upgrades
        # ═══════════════════════════════════════════════════════════════
        elif 'shopify.com' in url or 'cdn.shopify' in url:
            # Remove size parameters like _100x100, _small, _medium
            url = re.sub(r'_\d+x\d+\.', '.', url)
            url = re.sub(r'_(small|medium|large|grande|master)\.', '.', url, flags=re.IGNORECASE)
        
        # ═══════════════════════════════════════════════════════════════
        # Generic Query Parameter Cleanup
        # ═══════════════════════════════════════════════════════════════
        # Remove common size/quality query parameters
        if '?' in url:
            base_url = url.split('?')[0]
            # Only keep the base URL if it looks like a valid image
            if any(base_url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']):
                url = base_url
        
        return url
    
    def _sort_by_quality(self, images: List[str]) -> List[str]:
        """
        Sort images by quality indicators
        
        Scoring system:
        - High resolution indicators: +100
        - Medium resolution: +50
        - Known reliable hosts: +30
        - Main/primary image indicators: +20
        - Thumbnail indicators: -50
        """
        
        def quality_score(url: str) -> int:
            score = 0
            url_lower = url.lower()
            
            # ═══════════════════════════════════════════════════════════
            # Resolution scoring
            # ═══════════════════════════════════════════════════════════
            # High resolution indicators (+100)
            high_res_patterns = [
                's-l1600', 's-l1200', '_1600', '_1200', '_1024',
                'large', 'full', 'original', 'master', 'zoom'
            ]
            for pattern in high_res_patterns:
                if pattern in url_lower:
                    score += 100
                    break
            
            # Medium resolution indicators (+50)
            med_res_patterns = ['s-l800', 's-l500', '_800', '_500', 'medium']
            for pattern in med_res_patterns:
                if pattern in url_lower:
                    score += 50
                    break
            
            # ═══════════════════════════════════════════════════════════
            # Host reliability scoring
            # ═══════════════════════════════════════════════════════════
            reliable_hosts = [
                ('ebayimg.com', 40),
                ('alicdn.com', 35),
                ('amazon', 35),
                ('shopify.com', 30),
                ('cloudinary.com', 30),
                ('imgix.net', 30),
                ('etsystatic.com', 30),
                ('cloudfront.net', 25),
            ]
            for host, host_score in reliable_hosts:
                if host in url_lower:
                    score += host_score
                    break
            
            # ═══════════════════════════════════════════════════════════
            # Position/type indicators
            # ═══════════════════════════════════════════════════════════
            # Main/primary image indicators (+20)
            main_patterns = [
                'main', 'primary', 'hero', 'featured',
                '_1.', '_01.', '-1.', '-01.', '/1.', '/01.',
                'front', 'cover'
            ]
            for pattern in main_patterns:
                if pattern in url_lower:
                    score += 20
                    break
            
            # ═══════════════════════════════════════════════════════════
            # Penalty scoring (negative)
            # ═══════════════════════════════════════════════════════════
            # Thumbnail/small indicators (-50)
            thumb_patterns = [
                'thumb', 'small', 'tiny', 'mini', 'icon',
                's-l64', 's-l96', 's-l140', 's-l225',
                '_64', '_96', '_100', '_150', '_200',
                'preview', 'crop'
            ]
            for pattern in thumb_patterns:
                if pattern in url_lower:
                    score -= 50
                    break
            
            # Penalize very long URLs (might be tracking URLs)
            if len(url) > 500:
                score -= 20
            
            return score
        
        return sorted(images, key=quality_score, reverse=True)
    
    def _clean_image_url(self, url: str) -> str:
        """Clean and improve image URL"""
        if not url:
            return ''

        url = url.strip()

        # Remove escape characters
        url = url.replace('\\/', '/')
        url = url.replace('\\"', '')
        
        # Remove trailing characters that shouldn't be there
        url = url.rstrip('"\'>,;)}]')
        
        # Fix double protocols
        if url.count('http') > 1:
            idx = url.rfind('http')
            url = url[idx:]
        
        return url
    
    def _clean_price_value(self, value: Union[str, int, float, Dict, None]) -> Optional[float]:
        """Clean price value"""

        if value is None:
            return None

        try:
            # If dictionary (e.g., {"value": 10, "currency": "USD"})
            if isinstance(value, dict):
                if 'value' in value:
                    return float(value['value'])
                elif 'amount' in value:
                    return float(value['amount'])

            # If string
            if isinstance(value, str):
                # Remove currency and symbols
                cleaned = ''.join(c for c in value if c.isdigit() or c == '.')
                if cleaned:
                    return float(cleaned)

            # If number
            return float(value)
            
        except:
            return None
    
    # ═══════════════════════════════════════════════════════════════════
    # Product processing and parsing
    # ═══════════════════════════════════════════════════════════════════

    def _parse_product(self, item: Dict) -> Optional[Dict]:
        """Parse and prepare product for upload"""

        product = item['product']

        # Basic data
        title = product.get('title', product.get('name', ''))
        price = self._extract_price(product)
        images = self._extract_images(product)
        
        if not title or not price:
            return None

        # Rewrite title
        rewritten_title = self._rewrite_title(title)

        # Create dynamic description (Professional Minimal)
        description = self._create_professional_description(product, title, price)

        # Seller info (for Google Sheet)
        seller_info = self._extract_seller_info(product)
        
        original_price = price / 1.4
        profit_margin = ((price - original_price) / original_price) * 100
        
        return {
            "title": rewritten_title,
            "original_title": title,
            "description": description,
            "price": f"{price:.2f}",
            "images": images if images else [''],
            "product_url": product.get('link', product.get('url', '')),
            "ebay_price": round(original_price, 2),
            "profit_margin": round(profit_margin, 1),
            "seller_info": seller_info,
            "sku": self._generate_sku(title),
            "stock": 50,
            "image_count": len(images),
            "item_id": product.get('item_id', product.get('id', product.get('itemId')))
        }
    
    def _rewrite_title(self, title: str) -> str:
        """Rewrite title"""

        # Remove unwanted words
        unwanted = ['Cheap', 'China', 'Wholesale', 'Dropship', 'Factory', 'Hot Sale', 'New Arrival']
        for word in unwanted:
            title = title.replace(word, '')
            title = title.replace(word.lower(), '')

        # Improvements
        replacements = {
            'For iPhone': 'Compatible with iPhone',
            'For Samsung': 'Compatible with Samsung',
            'for iPhone': 'Compatible with iPhone',
            'for Samsung': 'Compatible with Samsung',
        }

        for old, new in replacements.items():
            title = title.replace(old, new)

        # Clean and return
        title = ' '.join(title.split())  # Remove extra spaces
        title = title.strip()
        
        # Ensure proper capitalization
        if title:
            title = title[0].upper() + title[1:] if len(title) > 1 else title.upper()
        
        return title[:255]
    
    # ═══════════════════════════════════════════════════════════════════
    # Professional Minimal Product Description (Apple-style)
    # ═══════════════════════════════════════════════════════════════════
    
    def _detect_product_type(self, title: str) -> str:
        """Detect product type from title"""

        title_lower = title.lower()

        # List of types and keywords
        types = {
            'airpods': ['airpod', 'earpods', 'earbuds', 'tws'],
            'phone_case': ['case', 'cover', 'bumper', 'pouch'],
            'charger': ['charger', 'adapter', 'charging'],
            'cable': ['cable', 'cord', 'wire', 'usb'],
            'headphones': ['headphone', 'headset', 'earphone'],
            'watch': ['watch', 'band', 'strap', 'smartwatch'],
            'screen': ['screen', 'protector', 'tempered', 'glass'],
            'holder': ['holder', 'stand', 'mount', 'grip'],
            'power_bank': ['power bank', 'battery', 'powerbank'],
            'speaker': ['speaker', 'bluetooth', 'wireless speaker']
        }
        
        for type_name, keywords in types.items():
            for keyword in keywords:
                if keyword in title_lower:
                    return type_name
                    
        return 'accessory'
    
    def _create_professional_description(self, product: Dict, title: str, price: float) -> str:
        """
        Create a professional, minimal, black & white product description
        
        Style: Apple / Enterprise SaaS / Premium Shopify
        - White background
        - Black / dark gray text
        - No gradients
        - No emojis
        - No marketing hype
        - Focus on clarity, specifications, compatibility
        """
        
        product_type = self._detect_product_type(title)
        
        # Extract any specifications from product data
        specs = self._extract_specifications(product, product_type)
        
        # Get compatibility info
        compatibility = self._extract_compatibility(title, product)
        
        # Template data by product type
        templates = {
            'phone_case': {
                'category': 'Protective Case',
                'features': [
                    'Precision-engineered fit for exact device compatibility',
                    'Impact-resistant materials for reliable protection',
                    'Raised bezels protect screen and camera from surface contact',
                    'Full access to all ports, buttons, and features',
                    'Slim profile maintains comfortable grip'
                ]
            },
            'charger': {
                'category': 'Charging Accessory',
                'features': [
                    'Optimized power delivery for efficient charging',
                    'Built-in safety protections against overcharge and overheating',
                    'Compact design for portability',
                    'Universal compatibility with standard devices',
                    'Durable construction for long-term reliability'
                ]
            },
            'cable': {
                'category': 'Data & Charging Cable',
                'features': [
                    'High-speed data transfer capability',
                    'Reinforced connectors for durability',
                    'Flexible cable design resists tangling',
                    'Compatible with fast charging protocols',
                    'Quality materials for extended lifespan'
                ]
            },
            'headphones': {
                'category': 'Audio Device',
                'features': [
                    'Clear audio reproduction across frequencies',
                    'Comfortable ergonomic design for extended use',
                    'Passive noise isolation for focused listening',
                    'Built-in microphone for calls',
                    'Lightweight construction for portability'
                ]
            },
            'airpods': {
                'category': 'Wireless Earphones',
                'features': [
                    'True wireless design for complete freedom of movement',
                    'Stable Bluetooth connectivity',
                    'Compact charging case included',
                    'Touch controls for playback and calls',
                    'Compatible with iOS and Android devices'
                ]
            },
            'watch': {
                'category': 'Smart Watch Accessory',
                'features': [
                    'Designed for precise watch model compatibility',
                    'Durable materials suitable for daily wear',
                    'Secure fastening mechanism',
                    'Comfortable for all-day use',
                    'Easy installation without tools'
                ]
            },
            'screen': {
                'category': 'Screen Protection',
                'features': [
                    'Tempered glass with high hardness rating',
                    'Oleophobic coating reduces fingerprints',
                    'Precise cutouts for sensors and cameras',
                    'Maintains touch sensitivity and display clarity',
                    'Easy bubble-free installation'
                ]
            },
            'default': {
                'category': 'Electronic Accessory',
                'features': [
                    'Quality materials and construction',
                    'Designed for reliable performance',
                    'Compatible with standard devices',
                    'Compact and portable design',
                    'Practical solution for everyday use'
                ]
            }
        }
        
        template = templates.get(product_type, templates['default'])
        
        # Build the professional HTML description
        html = f'''
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 720px; margin: 0 auto; padding: 24px; color: #1a1a1a; background: #ffffff; line-height: 1.6;">

    <div style="border-bottom: 1px solid #e5e5e5; padding-bottom: 20px; margin-bottom: 24px;">
        <p style="font-size: 13px; color: #666666; margin: 0 0 8px 0; text-transform: uppercase; letter-spacing: 0.5px;">
            {template['category']}
        </p>
        <h1 style="font-size: 24px; font-weight: 600; color: #1a1a1a; margin: 0; line-height: 1.3;">
            {self._clean_title_for_description(title)}
        </h1>
    </div>
'''
        
        # Compatibility section (if available)
        if compatibility:
            html += f'''
    <div style="margin-bottom: 24px;">
        <h2 style="font-size: 14px; font-weight: 600; color: #1a1a1a; margin: 0 0 12px 0; text-transform: uppercase; letter-spacing: 0.5px;">
            Compatibility
        </h2>
        <p style="font-size: 15px; color: #333333; margin: 0;">
            {compatibility}
        </p>
    </div>
'''
        
        # Features section
        html += '''
    <div style="margin-bottom: 24px;">
        <h2 style="font-size: 14px; font-weight: 600; color: #1a1a1a; margin: 0 0 16px 0; text-transform: uppercase; letter-spacing: 0.5px;">
            Features
        </h2>
        <ul style="list-style: none; padding: 0; margin: 0;">
'''
        
        for feature in template['features']:
            html += f'''
            <li style="padding: 10px 0; border-bottom: 1px solid #f0f0f0; font-size: 15px; color: #333333;">
                {feature}
            </li>
'''
        
        html += '''
        </ul>
    </div>
'''
        
        # Specifications section (if available)
        if specs:
            html += '''
    <div style="margin-bottom: 24px;">
        <h2 style="font-size: 14px; font-weight: 600; color: #1a1a1a; margin: 0 0 16px 0; text-transform: uppercase; letter-spacing: 0.5px;">
            Specifications
        </h2>
        <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
'''
            for spec_name, spec_value in specs.items():
                html += f'''
            <tr>
                <td style="padding: 10px 0; border-bottom: 1px solid #f0f0f0; color: #666666; width: 40%;">{spec_name}</td>
                <td style="padding: 10px 0; border-bottom: 1px solid #f0f0f0; color: #1a1a1a;">{spec_value}</td>
            </tr>
'''
            html += '''
        </table>
    </div>
'''
        
        # Package contents
        html += f'''
    <div style="margin-bottom: 24px;">
        <h2 style="font-size: 14px; font-weight: 600; color: #1a1a1a; margin: 0 0 12px 0; text-transform: uppercase; letter-spacing: 0.5px;">
            Package Contents
        </h2>
        <p style="font-size: 15px; color: #333333; margin: 0;">
            1 x {template['category']}
        </p>
    </div>
'''
        
        # Shipping & Returns
        html += '''
    <div style="background: #f9f9f9; padding: 20px; margin-top: 24px;">
        <h2 style="font-size: 14px; font-weight: 600; color: #1a1a1a; margin: 0 0 12px 0; text-transform: uppercase; letter-spacing: 0.5px;">
            Shipping & Returns
        </h2>
        <p style="font-size: 14px; color: #666666; margin: 0 0 8px 0;">
            Standard shipping: 7-14 business days
        </p>
        <p style="font-size: 14px; color: #666666; margin: 0;">
            30-day return policy for unused items in original packaging
        </p>
    </div>

</div>
'''
        
        return html.strip()
    
    def _clean_title_for_description(self, title: str) -> str:
        """Clean title for use in description header"""
        
        # Remove excessive capitalization
        if title.isupper():
            title = title.title()
        
        # Remove common marketing words
        remove_words = ['NEW', 'HOT', 'SALE', '!!!', '---', '***', 'BEST', 'TOP']
        for word in remove_words:
            title = title.replace(word, '')
        
        # Clean up
        title = ' '.join(title.split())
        
        return title[:100]
    
    def _extract_specifications(self, product: Dict, product_type: str) -> Dict:
        """Extract product specifications from available data"""
        
        specs = {}
        
        # Try to get specs from product data
        spec_fields = ['specifications', 'specs', 'attributes', 'details', 'properties']
        
        for field in spec_fields:
            if field in product and isinstance(product[field], dict):
                for key, value in product[field].items():
                    if value and str(value).strip():
                        specs[key.replace('_', ' ').title()] = str(value)
        
        # Add common specs if available
        if 'material' in product:
            specs['Material'] = str(product['material'])
        if 'color' in product:
            specs['Color'] = str(product['color'])
        if 'weight' in product:
            specs['Weight'] = str(product['weight'])
        if 'dimensions' in product:
            specs['Dimensions'] = str(product['dimensions'])
        
        # Limit to 6 specs max
        return dict(list(specs.items())[:6])
    
    def _extract_compatibility(self, title: str, product: Dict) -> str:
        """Extract device compatibility from title and product data"""
        
        title_lower = title.lower()
        compatibility = []
        
        # iPhone models
        iphone_models = ['iphone 16', 'iphone 15', 'iphone 14', 'iphone 13', 'iphone 12', 'iphone 11', 
                        'iphone se', 'iphone x', 'iphone xs', 'iphone xr', 'iphone pro', 'iphone plus', 'iphone max']
        for model in iphone_models:
            if model in title_lower:
                compatibility.append(model.replace('iphone', 'iPhone'))
        
        # Samsung models
        samsung_patterns = [
            ('galaxy s24', 'Galaxy S24'), ('galaxy s23', 'Galaxy S23'), ('galaxy s22', 'Galaxy S22'),
            ('galaxy a54', 'Galaxy A54'), ('galaxy a53', 'Galaxy A53'), ('galaxy note', 'Galaxy Note'),
            ('galaxy z fold', 'Galaxy Z Fold'), ('galaxy z flip', 'Galaxy Z Flip')
        ]
        for pattern, display in samsung_patterns:
            if pattern in title_lower:
                compatibility.append(f'Samsung {display}')
        
        # From product data
        if 'compatibility' in product:
            compat_data = product['compatibility']
            if isinstance(compat_data, str):
                return compat_data
            elif isinstance(compat_data, list):
                compatibility.extend(compat_data)
        
        if compatibility:
            # Deduplicate and join
            unique = list(dict.fromkeys(compatibility))
            return ', '.join(unique[:5])
        
        return ''
    
    def _extract_seller_info(self, product: Dict) -> Dict:
        """Extract seller information"""
        
        return {
            'seller_name': product.get('seller', product.get('seller_name', 'eBay Seller')),
            'seller_rating': product.get('seller_rating', 'N/A'),
            'seller_url': product.get('seller_url', ''),
            'location': product.get('location', product.get('ship_from', 'China'))
        }
    
    def _generate_sku(self, title: str) -> str:
        """Generate SKU"""
        hash_obj = hashlib.md5(title.encode())
        return f"EBAY_{hash_obj.hexdigest()[:8].upper()}"
    
    # ═══════════════════════════════════════════════════════════════════
    # Upload products to Shopify
    # ═══════════════════════════════════════════════════════════════════

    def upload_to_shopify(self, product: Dict) -> bool:
        """Upload single product to Shopify"""
        
        shopify_data = {
            "product": {
                "title": product["title"][:255],
                "body_html": product["description"],
                "vendor": "Premium Supplier",
                "product_type": "Electronics Accessories",
                "tags": "electronics, accessories, premium",
                "variants": [{
                    "price": product["price"],
                    "sku": product["sku"],
                    "inventory_management": "shopify",
                    "inventory_quantity": product["stock"]
                }]
            }
        }
        
        if product.get("images"):
            shopify_data["product"]["images"] = [{"src": img} for img in product["images"] if img]
        
        try:
            response = requests.post(
                f"{self.shopify_url}/products.json",
                headers=self.shopify_headers,
                json=shopify_data,
                timeout=30
            )
            
            if response.status_code == 201:
                return True
            else:
                print(f"   [ERROR] Failed: {response.status_code}")
                if response.text:
                    print(f"   Details: {response.text[:200]}")
                return False
        
        except Exception as e:
            print(f"   [ERROR] {str(e)}")
            return False
    
    # ═══════════════════════════════════════════════════════════════════
    # CSV Report Generation
    # ═══════════════════════════════════════════════════════════════════
    
    def generate_csv_report(self, products: List[Dict], filename: str = None) -> str:
        """
        Generate a CSV report of selected products for manual review
        
        Columns:
        - Product Title
        - Original Title
        - Shopify Price
        - Source Price
        - Profit Margin %
        - Product URL
        - Seller Name
        - Seller Rating
        - Image Count
        - Final Score
        - SKU
        """
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            reports_dir = os.path.join("data", "reports")
            os.makedirs(reports_dir, exist_ok=True)
            filename = os.path.join(reports_dir, f"product_import_report_{timestamp}.csv")
        
        headers = [
            'Product Title',
            'Original Title',
            'Shopify Price',
            'Source Price',
            'Profit Margin %',
            'Product URL',
            'Seller Name',
            'Seller Rating',
            'Image Count',
            'Final Score',
            'SKU'
        ]
        
        rows = []
        for product in products:
            seller_info = product.get('seller_info', {})
            row = [
                product.get('title', ''),
                product.get('original_title', ''),
                f"${product.get('price', '0.00')}",
                f"${product.get('ebay_price', 0):.2f}",
                f"{product.get('profit_margin', 0):.1f}%",
                product.get('product_url', ''),
                seller_info.get('seller_name', 'N/A'),
                seller_info.get('seller_rating', 'N/A'),
                str(product.get('image_count', len(product.get('images', [])))),
                str(int(product.get('final_score', 0))),
                product.get('sku', '')
            ]
            rows.append(row)
        
        # Write CSV
        try:
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                writer.writerows(rows)
            
            print(f"\n[OK] CSV Report generated: {filename}")
            print(f"     Total products: {len(rows)}")
            return filename
        
        except Exception as e:
            print(f"[ERROR] Failed to generate CSV: {str(e)}")
            return ''
    
    def generate_google_sheets_data(self, products: List[Dict]) -> List[List]:
        """
        Generate data formatted for Google Sheets API
        Returns a 2D list that can be directly used with gspread or Google Sheets API
        """
        
        headers = [
            'Product Title',
            'Original Title',
            'Shopify Price',
            'Source Price',
            'Profit Margin %',
            'Product URL',
            'Seller Name',
            'Seller Rating',
            'Image Count',
            'Final Score',
            'SKU',
            'Status'
        ]
        
        data = [headers]
        
        for product in products:
            seller_info = product.get('seller_info', {})
            row = [
                product.get('title', ''),
                product.get('original_title', ''),
                float(product.get('price', '0.00')),
                product.get('ebay_price', 0),
                product.get('profit_margin', 0),
                product.get('product_url', ''),
                seller_info.get('seller_name', 'N/A'),
                seller_info.get('seller_rating', 'N/A'),
                len(product.get('images', [])),
                int(product.get('final_score', 0)),
                product.get('sku', ''),
                'Pending Review'
            ]
            data.append(row)
        
        return data
    
    # ═══════════════════════════════════════════════════════════════════
    # Email Report Functionality
    # ═══════════════════════════════════════════════════════════════════
    
    def send_report_email(self, csv_file: str, products: List[Dict], recipient_email: str = None) -> bool:
        """
        Send the CSV report via email to the customer
        
        Args:
            csv_file: Path to the CSV report file
            products: List of imported products
            recipient_email: Customer email (overrides self.customer_email)
        
        Returns:
            bool: True if email sent successfully
        """
        
        # Determine recipient
        to_email = recipient_email or self.customer_email
        
        if not to_email:
            print("[WARN] No recipient email provided, skipping email send")
            return False
        
        if not csv_file or not os.path.exists(csv_file):
            print("[ERROR] CSV file not found, cannot send email")
            return False
        
        print(f"\n[INFO] Sending report to: {to_email}")
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Product Import Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            msg['From'] = f"{self.email_config['from_name']} <{self.email_config['from_email']}>"
            msg['To'] = to_email
            
            # Calculate summary stats
            total_products = len(products)
            total_value = sum(float(p.get('price', 0)) for p in products)
            avg_margin = sum(p.get('profit_margin', 0) for p in products) / max(total_products, 1)
            avg_score = sum(p.get('final_score', 0) for p in products) / max(total_products, 1)
            
            # Plain text version
            text_content = f"""
Product Import Report
=====================

Store: {self.shopify_store}
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Summary:
- Total Products: {total_products}
- Total Value: ${total_value:.2f}
- Average Profit Margin: {avg_margin:.1f}%
- Average Quality Score: {avg_score:.0f}/170

Products Imported:
"""
            for i, p in enumerate(products, 1):
                text_content += f"\n{i}. {p.get('title', 'N/A')[:50]}"
                text_content += f"\n   Price: ${p.get('price', '0.00')} | Score: {p.get('final_score', 'N/A')}"
            
            text_content += f"""

Please review the attached CSV file for full details.

---
This is an automated message from your Product Import System.
"""
            
            # HTML version
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            color: #1a1a1a;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: #1a1a1a;
            color: #ffffff;
            padding: 24px;
            text-align: center;
            margin-bottom: 24px;
        }}
        .header h1 {{
            margin: 0;
            font-size: 24px;
            font-weight: 600;
        }}
        .stats {{
            display: flex;
            flex-wrap: wrap;
            gap: 16px;
            margin-bottom: 24px;
        }}
        .stat-box {{
            flex: 1;
            min-width: 120px;
            background: #f5f5f5;
            padding: 16px;
            text-align: center;
            border-radius: 8px;
        }}
        .stat-value {{
            font-size: 28px;
            font-weight: 700;
            color: #1a1a1a;
        }}
        .stat-label {{
            font-size: 12px;
            color: #666666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .products-table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 24px;
        }}
        .products-table th {{
            background: #f5f5f5;
            padding: 12px;
            text-align: left;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #666666;
            border-bottom: 2px solid #e0e0e0;
        }}
        .products-table td {{
            padding: 12px;
            border-bottom: 1px solid #e0e0e0;
            font-size: 14px;
        }}
        .score-badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
        }}
        .score-high {{
            background: #d4edda;
            color: #155724;
        }}
        .score-medium {{
            background: #fff3cd;
            color: #856404;
        }}
        .score-low {{
            background: #f8d7da;
            color: #721c24;
        }}
        .footer {{
            margin-top: 32px;
            padding-top: 16px;
            border-top: 1px solid #e0e0e0;
            font-size: 12px;
            color: #999999;
            text-align: center;
        }}
        .cta {{
            background: #1a1a1a;
            color: #ffffff;
            padding: 12px 24px;
            text-decoration: none;
            display: inline-block;
            border-radius: 6px;
            font-weight: 600;
            margin-top: 16px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Product Import Report</h1>
    </div>
    
    <p style="color: #666666; margin-bottom: 24px;">
        <strong>Store:</strong> {self.shopify_store}<br>
        <strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    </p>
    
    <table style="width: 100%; margin-bottom: 24px;">
        <tr>
            <td style="background: #f5f5f5; padding: 16px; text-align: center; border-radius: 8px; width: 25%;">
                <div style="font-size: 28px; font-weight: 700; color: #1a1a1a;">{total_products}</div>
                <div style="font-size: 12px; color: #666666; text-transform: uppercase;">Products</div>
            </td>
            <td style="width: 4%;"></td>
            <td style="background: #f5f5f5; padding: 16px; text-align: center; border-radius: 8px; width: 25%;">
                <div style="font-size: 28px; font-weight: 700; color: #1a1a1a;">${total_value:.0f}</div>
                <div style="font-size: 12px; color: #666666; text-transform: uppercase;">Total Value</div>
            </td>
            <td style="width: 4%;"></td>
            <td style="background: #f5f5f5; padding: 16px; text-align: center; border-radius: 8px; width: 25%;">
                <div style="font-size: 28px; font-weight: 700; color: #1a1a1a;">{avg_margin:.0f}%</div>
                <div style="font-size: 12px; color: #666666; text-transform: uppercase;">Avg Margin</div>
            </td>
            <td style="width: 4%;"></td>
            <td style="background: #f5f5f5; padding: 16px; text-align: center; border-radius: 8px; width: 25%;">
                <div style="font-size: 28px; font-weight: 700; color: #1a1a1a;">{avg_score:.0f}</div>
                <div style="font-size: 12px; color: #666666; text-transform: uppercase;">Avg Score</div>
            </td>
        </tr>
    </table>
    
    <h2 style="font-size: 16px; font-weight: 600; color: #1a1a1a; margin-bottom: 16px;">
        Imported Products
    </h2>
    
    <table class="products-table">
        <thead>
            <tr>
                <th>#</th>
                <th>Product</th>
                <th>Price</th>
                <th>Score</th>
            </tr>
        </thead>
        <tbody>
"""
            
            for i, p in enumerate(products[:10], 1):  # Show first 10 in email
                score = p.get('final_score', 0)
                if score >= 100:
                    score_class = 'score-high'
                elif score >= 70:
                    score_class = 'score-medium'
                else:
                    score_class = 'score-low'
                
                html_content += f"""
            <tr>
                <td style="color: #999999;">{i}</td>
                <td>{p.get('title', 'N/A')[:45]}...</td>
                <td>${p.get('price', '0.00')}</td>
                <td><span class="score-badge {score_class}">{score:.0f}</span></td>
            </tr>
"""
            
            if len(products) > 10:
                html_content += f"""
            <tr>
                <td colspan="4" style="text-align: center; color: #666666; font-style: italic;">
                    + {len(products) - 10} more products in attached CSV
                </td>
            </tr>
"""
            
            html_content += f"""
        </tbody>
    </table>
    
    <div style="text-align: center; margin: 32px 0;">
        <p style="color: #666666; margin-bottom: 16px;">
            Please review the attached CSV file for complete product details.
        </p>
        <a href="https://{self.shopify_store}/admin/products" class="cta">
            View in Shopify Admin
        </a>
    </div>
    
    <div class="footer">
        <p>This is an automated message from your Product Import System.</p>
        <p>Report generated on {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}</p>
    </div>
</body>
</html>
"""
            
            # Attach text and HTML parts
            part1 = MIMEText(text_content, 'plain')
            part2 = MIMEText(html_content, 'html')
            msg.attach(part1)
            msg.attach(part2)
            
            # Attach CSV file
            with open(csv_file, 'rb') as f:
                attachment = MIMEBase('application', 'octet-stream')
                attachment.set_payload(f.read())
                encoders.encode_base64(attachment)
                attachment.add_header(
                    'Content-Disposition',
                    f'attachment; filename="{os.path.basename(csv_file)}"'
                )
                msg.attach(attachment)
            
            # Send email
            smtp_server = self.email_config['smtp_server']
            smtp_port = self.email_config['smtp_port']
            smtp_username = self.email_config['smtp_username']
            smtp_password = self.email_config['smtp_password']
            
            # Check if SMTP is configured
            if not smtp_username or not smtp_password:
                print("[WARN] SMTP credentials not configured")
                print("[INFO] To enable email, set environment variables:")
                print("       SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, FROM_EMAIL")
                
                # Fallback: Save email content to file for manual sending
                email_backup_file = csv_file.replace('.csv', '_email.html')
                with open(email_backup_file, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                print(f"[INFO] Email content saved to: {email_backup_file}")
                return False
            
            # Connect and send
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_username, smtp_password)
                server.send_message(msg)
            
            print(f"[OK] Report email sent successfully to: {to_email}")
            return True
            
        except smtplib.SMTPAuthenticationError:
            print("[ERROR] SMTP authentication failed. Check username/password.")
            print("[INFO] For Gmail, use an App Password: https://support.google.com/accounts/answer/185833")
            return False
        except smtplib.SMTPException as e:
            print(f"[ERROR] SMTP error: {str(e)}")
            return False
        except Exception as e:
            print(f"[ERROR] Failed to send email: {str(e)}")
            return False
    
    def configure_email(self, smtp_server: str = None, smtp_port: int = None,
                       smtp_username: str = None, smtp_password: str = None,
                       from_email: str = None, from_name: str = None):
        """
        Configure email settings programmatically
        
        Args:
            smtp_server: SMTP server address (e.g., 'smtp.gmail.com')
            smtp_port: SMTP port (usually 587 for TLS)
            smtp_username: SMTP username/email
            smtp_password: SMTP password (use App Password for Gmail)
            from_email: Sender email address
            from_name: Sender display name
        """
        if smtp_server:
            self.email_config['smtp_server'] = smtp_server
        if smtp_port:
            self.email_config['smtp_port'] = smtp_port
        if smtp_username:
            self.email_config['smtp_username'] = smtp_username
        if smtp_password:
            self.email_config['smtp_password'] = smtp_password
        if from_email:
            self.email_config['from_email'] = from_email
        if from_name:
            self.email_config['from_name'] = from_name
        
        print("[OK] Email configuration updated")
    
    # ═══════════════════════════════════════════════════════════════════
    # Main operation
    # ═══════════════════════════════════════════════════════════════════

    def import_products(self, search_category: str = "phone case",
                        generate_report: bool = True,
                        send_email: bool = True,
                        recipient_email: str = None) -> Dict:
        """
        Import products from API to Shopify
        
        Args:
            search_category: Product category to search
            generate_report: Whether to generate CSV report
            send_email: Whether to send report via email
            recipient_email: Override customer email for this import
        """
        
        print("=" * 70)
        print(f"PRODUCT IMPORT - {self.max_products} products from API to Shopify")
        print("=" * 70)
        print(f"Store: {self.shopify_store}")
        print(f"Quantity: {self.max_products}")
        print(f"Category: {search_category}")
        if send_email:
            print(f"Email Report To: {recipient_email or self.customer_email or 'Not configured'}")
        print("=" * 70 + "\n")
        
        # Read products from API
        products = self.load_ebay_products(search_category=search_category)
        
        if not products:
            print("\n[ERROR] No products to import")
            return {
                "success": False,
                "message": "No products found in API",
                "uploaded": 0,
                "failed": 0
            }
        
        print(f"[OK] Ready to upload {len(products)} products\n")

        # ═══════════════════════════════════════════════════════════════
        # STEP: Enhance images from API (NEW)
        # ═══════════════════════════════════════════════════════════════
        print("\n" + "=" * 70)
        print("STEP: ENHANCING IMAGES FROM API")
        print("=" * 70 + "\n")

        self._enhance_products_batch(products)

        print(f"\n[INFO] Waiting 5 seconds for image processing to complete...")
        time.sleep(5)
        print("[OK] Image enhancement complete\n")

        # ═══════════════════════════════════════════════════════════════
        # Generate CSV report before upload
        # ═══════════════════════════════════════════════════════════════
        report_file = ''
        if generate_report:
            report_file = self.generate_csv_report(products)
        
        # Upload products
        success = 0
        failed = 0
        uploaded_products = []
        
        for i, product in enumerate(products, 1):
            print(f"[{i}/{len(products)}] {product['title'][:50]}...")

            # ═══════════════════════════════════════════════════════════════
            # Extract images if not already present
            # ═══════════════════════════════════════════════════════════════
            if 'images' not in product or not product['images']:
                product['images'] = self._extract_images(product)

            print(f"    Price: ${product['price']} | Images: {len(product.get('images', []))} | Score: {product.get('final_score', 'N/A')}")

            if self.upload_to_shopify(product):
                success += 1
                uploaded_products.append(product)
                print(f"    [OK] Uploaded successfully\n")
            else:
                failed += 1
                print(f"    [FAILED] Upload failed\n")
            
            # Small delay between products
            if i < len(products):
                time.sleep(1.5)
        
        # Send email report
        email_sent = False
        if send_email and report_file:
            email_sent = self.send_report_email(
                csv_file=report_file,
                products=uploaded_products if uploaded_products else products,
                recipient_email=recipient_email
            )
        
        # Summary
        print("\n" + "=" * 70)
        print("IMPORT SUMMARY")
        print("=" * 70)
        print(f"Successful: {success} products")
        print(f"Failed: {failed} products")
        print(f"Success Rate: {(success/len(products)*100):.0f}%")
        
        if report_file:
            print(f"\nCSV Report: {report_file}")
        
        if email_sent:
            print(f"Email Sent: Yes (to {recipient_email or self.customer_email})")
        elif send_email:
            print(f"Email Sent: No (check SMTP configuration)")
        
        if uploaded_products:
            print("\nUploaded Products:")
            for i, p in enumerate(uploaded_products, 1):
                print(f"  {i}. {p['title'][:55]}...")
        
        print("\n" + "=" * 70)
        print(f"COMPLETE! Check your store:")
        print(f"https://{self.shopify_store}/admin/products")
        print("=" * 70)
        
        return {
            "success": True,
            "message": f"Successfully imported {success} products",
            "uploaded": success,
            "failed": failed,
            "products": uploaded_products,
            "store_url": f"https://{self.shopify_store}",
            "report_file": report_file,
            "email_sent": email_sent
        }


# ═══════════════════════════════════════════════════════════════════
# Wrapper Class for compatibility with app.py
# ═══════════════════════════════════════════════════════════════════

class ProductImporter:
    """
    Wrapper class for compatibility with app.py
    """
    
    def __init__(self, access_token: str, store_url: str, customer_email: str = None):
        self.access_token = access_token
        self.store_url = store_url.replace('https://', '').replace('http://', '').split('/')[0]
        self.customer_email = customer_email
        print(f"ProductImporter initialized for store: {self.store_url}")
        if customer_email:
            print(f"Customer email: {customer_email}")
    
    def import_products(self, category: str = 'electronics', count: int = 5, 
                       send_email: bool = True) -> List[Dict]:
        print(f"\n{'='*70}")
        print(f"Starting product import")
        print(f"Category: {category} | Count: {count}")
        print(f"{'='*70}\n")
        
        importer = EbayShopifyImporter(
            shopify_store=self.store_url,
            access_token=self.access_token,
            max_products=count,
            customer_email=self.customer_email
        )
        
        result = importer.import_products(
            search_category=category,
            generate_report=True,
            send_email=send_email,
            recipient_email=self.customer_email
        )
        
        if result.get('success'):
            return result.get('products', [])
        else:
            return []
    
    def configure_email(self, smtp_server: str, smtp_port: int,
                       smtp_username: str, smtp_password: str,
                       from_email: str, from_name: str = "Product Import System"):
        """Configure SMTP settings for the wrapper"""
        self._email_config = {
            'smtp_server': smtp_server,
            'smtp_port': smtp_port,
            'smtp_username': smtp_username,
            'smtp_password': smtp_password,
            'from_email': from_email,
            'from_name': from_name
        }
        print("[OK] Email configuration saved")



    
    # ═══════════════════════════════════════════════════════════════
    # SMTP setup for sending email
    # ═══════════════════════════════════════════════════════════════
    # 
    # Option 1: Set environment variables (recommended for production)
    # export SMTP_SERVER=smtp.gmail.com
    # export SMTP_PORT=587
    # export SMTP_USERNAME=your-email@gmail.com
    # export SMTP_PASSWORD=your-app-password
    # export FROM_EMAIL=your-email@gmail.com
    # export FROM_NAME="Your Store Name"
    #
    # Option 2: Configure programmatically
    # importer.configure_email(
    #     smtp_server='smtp.gmail.com',
    #     smtp_port=587,
    #     smtp_username='your-email@gmail.com',
    #     smtp_password='your-app-password',  # Use Gmail App Password
    #     from_email='your-email@gmail.com',
    #     from_name='Your Store Name'
    # )
    #
    # For Gmail, you need to:
    # 1. Enable 2-Factor Authentication
    # 2. Generate an App Password: https://myaccount.google.com/apppasswords
    # 3. Use the App Password (not your regular password)
    # ═══════════════════════════════════════════════════════════════
    


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS - Run: python product.py test
# ═══════════════════════════════════════════════════════════════════════════════

def run_tests():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("RUNNING TESTS")
    print("=" * 70 + "\n")

    tests_passed = 0
    tests_failed = 0

    # ═══════════════════════════════════════════════════════════════════
    # Test 1: Endpoint Mapping
    # ═══════════════════════════════════════════════════════════════════
    print("[TEST 1] Endpoint Mapping...")

    importer = EbayShopifyImporter(
        shopify_store="test.myshopify.com",
        access_token="test_token",
        max_products=5
    )

    endpoint_mapping = {
        'phone case': ('cases', 'case'),
        'charger': ('chargers', 'charger'),
        'phone': ('phones', 'phone'),
        'tablet': ('tablets', 'tablet'),
        'airpods': ('audio', 'audio'),
        'watch': ('smartwatches', 'smartwatch'),
    }

    all_passed = True
    for category, (expected_endpoint, expected_type) in endpoint_mapping.items():
        result = endpoint_mapping.get(category)
        if result != (expected_endpoint, expected_type):
            print(f"   FAIL: '{category}' -> {result}, expected ({expected_endpoint}, {expected_type})")
            all_passed = False

    if all_passed:
        print("   PASS: All endpoint mappings correct")
        tests_passed += 1
    else:
        tests_failed += 1

    # ═══════════════════════════════════════════════════════════════════
    # Test 2: Keywords Mapping (No Duplicates)
    # ═══════════════════════════════════════════════════════════════════
    print("\n[TEST 2] Keywords - No Duplicates...")

    keywords1 = importer._get_search_keywords('phone case')
    keywords2 = importer._get_search_keywords('phone_case')
    keywords3 = importer._get_search_keywords('phone cases')

    if keywords1 == keywords2 == keywords3:
        print("   PASS: 'phone case', 'phone_case', 'phone cases' use same keywords")
        tests_passed += 1
    else:
        print("   FAIL: Keywords should be identical")
        tests_failed += 1

    # ═══════════════════════════════════════════════════════════════════
    # Test 3: Filter by Keywords - Phone Case
    # ═══════════════════════════════════════════════════════════════════
    print("\n[TEST 3] Filter - Phone Case only...")

    mock_products = [
        {'title': 'iPhone 15 Pro Case Clear Silicone', 'product_type': 'case'},
        {'title': 'Samsung Galaxy S24 Cover', 'product_type': 'case'},
        {'title': 'USB-C Fast Charger 65W', 'product_type': 'charger'},
        {'title': 'AirPods Pro 2 Earbuds', 'product_type': 'audio'},
        {'title': 'Apple Watch Band Sport', 'product_type': 'smartwatch'},
        {'title': 'Phone Case for iPhone 14', 'product_type': 'case'},
        {'title': 'Galaxy Buds 2 Pro Case', 'product_type': 'accessory'},
    ]

    keywords_case = importer._get_search_keywords('phone case')
    keywords_case['expected_product_type'] = 'case'

    filtered = importer._filter_by_keywords(mock_products, keywords_case, strict_mode=True)

    expected_count = 3  # iPhone 15, Galaxy S24, iPhone 14
    if len(filtered) == expected_count:
        print(f"   PASS: Got {len(filtered)} phone cases (expected {expected_count})")
        tests_passed += 1
    else:
        print(f"   FAIL: Got {len(filtered)} products, expected {expected_count}")
        for p in filtered:
            print(f"         - {p['title']}")
        tests_failed += 1

    # ═══════════════════════════════════════════════════════════════════
    # Test 4: Filter by Keywords - Charger only
    # ═══════════════════════════════════════════════════════════════════
    print("\n[TEST 4] Filter - Charger only...")

    keywords_charger = importer._get_search_keywords('charger')
    keywords_charger['expected_product_type'] = 'charger'

    filtered_chargers = importer._filter_by_keywords(mock_products, keywords_charger, strict_mode=True)

    expected_chargers = 1
    if len(filtered_chargers) == expected_chargers:
        print(f"   PASS: Got {len(filtered_chargers)} chargers (expected {expected_chargers})")
        tests_passed += 1
    else:
        print(f"   FAIL: Got {len(filtered_chargers)} products, expected {expected_chargers}")
        for p in filtered_chargers:
            print(f"         - {p['title']}")
        tests_failed += 1

    # ═══════════════════════════════════════════════════════════════════
    # Test 5: Negative Keywords Work
    # ═══════════════════════════════════════════════════════════════════
    print("\n[TEST 5] Negative keywords exclude correctly...")

    mock_with_negative = [
        {'title': 'iPhone 15 Case', 'product_type': 'case'},
        {'title': 'AirPods Case for iPhone', 'product_type': 'case'},
        {'title': 'Galaxy Buds Case Cover', 'product_type': 'case'},
        {'title': 'Samsung S24 Case', 'product_type': 'case'},
    ]

    filtered_no_audio = importer._filter_by_keywords(mock_with_negative, keywords_case, strict_mode=True)

    expected_no_audio = 2  # iPhone 15 and Samsung S24 only
    if len(filtered_no_audio) == expected_no_audio:
        print(f"   PASS: Excluded audio cases correctly, got {len(filtered_no_audio)}")
        tests_passed += 1
    else:
        print(f"   FAIL: Got {len(filtered_no_audio)}, expected {expected_no_audio}")
        for p in filtered_no_audio:
            print(f"         - {p['title']}")
        tests_failed += 1

    # ═══════════════════════════════════════════════════════════════════
    # Test 6: Required Keywords
    # ═══════════════════════════════════════════════════════════════════
    print("\n[TEST 6] Required keywords (case/cover)...")

    mock_no_required = [
        {'title': 'iPhone 15 Silicone Protection', 'product_type': 'case'},
        {'title': 'iPhone 15 Case Clear', 'product_type': 'case'},
        {'title': 'Samsung Galaxy Cover', 'product_type': 'case'},
    ]

    filtered_required = importer._filter_by_keywords(mock_no_required, keywords_case, strict_mode=True)

    expected_required = 2
    if len(filtered_required) == expected_required:
        print(f"   PASS: Required keywords work correctly, got {len(filtered_required)}")
        tests_passed += 1
    else:
        print(f"   FAIL: Got {len(filtered_required)}, expected {expected_required}")
        tests_failed += 1

    # ═══════════════════════════════════════════════════════════════════
    # Summary
    # ═══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print(f"TESTS COMPLETE: {tests_passed} passed, {tests_failed} failed")
    print("=" * 70)

    if tests_failed == 0:
        print("\nAll tests passed!")
        return True
    else:
        print(f"\n{tests_failed} test(s) failed!")
        return False



    # ═══════════════════════════════════════════════════════════════
    # SMTP setup for sending email
    # ═══════════════════════════════════════════════════════════════
    # 
    # Option 1: Set environment variables (recommended for production)
    # export SMTP_SERVER=smtp.gmail.com
    # export SMTP_PORT=587
    # export SMTP_USERNAME=your-email@gmail.com
    # export SMTP_PASSWORD=your-app-password
    # export FROM_EMAIL=your-email@gmail.com
    # export FROM_NAME="Your Store Name"
    #
    # Option 2: Configure programmatically
    # importer.configure_email(
    #     smtp_server='smtp.gmail.com',
    #     smtp_port=587,
    #     smtp_username='your-email@gmail.com',
    #     smtp_password='your-app-password',  # Use Gmail App Password
    #     from_email='your-email@gmail.com',
    #     from_name='Your Store Name'
    # )
    #
    # For Gmail, you need to:
    # 1. Enable 2-Factor Authentication
    # 2. Generate an App Password: https://myaccount.google.com/apppasswords
    # 3. Use the App Password (not your regular password)
    # ═══════════════════════════════════════════════════════════════
    
    # Import products
    result = importer.import_products(
        search_category="phone case",
        generate_report=True,   # Generate CSV report
        send_email=True,        # Send report via email
        recipient_email=CUSTOMER_EMAIL  # Or use None to use default customer_email
    )
    
    # Print result
    print(f"\nFinal Result:")
    print(f"   Status: {'SUCCESS' if result['success'] else 'FAILED'}")
    print(f"   Message: {result['message']}")
    print(f"   Uploaded: {result['uploaded']}")
    print(f"   Failed: {result['failed']}")
    if result.get('report_file'):
        print(f"   Report: {result['report_file']}")
    if result.get('email_sent'):
        print(f"   Email: Sent to {CUSTOMER_EMAIL}")