"""
Product Loader Mixin - API Loading & Keywords
Handles fetching products from API, keyword mapping, and fallback loading.
"""

import requests
from typing import List, Dict


class ProductLoaderMixin:
    """Mixin for loading products from API"""

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

        # Phone Cases keywords
        PHONE_CASE_KEYWORDS = {
            'positive': [
                'phone case', 'mobile case', 'cell phone', 'smartphone case',
                'iphone', 'iphone 16', 'iphone 15', 'iphone 14', 'iphone 13', 'iphone 12', 'iphone 11',
                'iphone se', 'iphone pro', 'iphone plus', 'iphone max',
                'samsung', 'galaxy',
                'galaxy s24', 'galaxy s23', 'galaxy s22', 'galaxy s21',
                'galaxy a54', 'galaxy a53', 'galaxy a34', 'galaxy a14',
                'galaxy note', 'galaxy z fold', 'galaxy z flip',
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

        CHARGER_KEYWORDS = {
            'positive': ['charger', 'charging', 'adapter', 'power adapter', 'fast charger', 'usb charger'],
            'required': [],
            'negative': ['case', 'cover', 'screen protector', 'tempered glass']
        }

        CABLE_KEYWORDS = {
            'positive': ['cable', 'cord', 'wire', 'usb-c', 'lightning', 'type-c'],
            'required': [],
            'negative': ['case', 'cover', 'screen protector']
        }

        AUDIO_KEYWORDS = {
            'positive': ['airpods', 'airpod', 'earbuds', 'earphones', 'headphones', 'headset', 'buds', 'tws'],
            'required': [],
            'negative': ['case', 'cover', 'phone', 'tablet', 'charger only']
        }

        WATCH_KEYWORDS = {
            'positive': ['watch', 'smartwatch', 'apple watch', 'galaxy watch', 'smart band'],
            'required': [],
            'negative': ['phone', 'case', 'tablet', 'charger']
        }

        PHONE_KEYWORDS = {
            'positive': ['iphone', 'samsung galaxy', 'smartphone', 'mobile phone', 'android phone'],
            'required': [],
            'negative': ['case', 'cover', 'charger', 'cable', 'screen protector']
        }

        TABLET_KEYWORDS = {
            'positive': ['tablet', 'ipad', 'galaxy tab', 'surface'],
            'required': [],
            'negative': ['phone', 'watch', 'case', 'cover']
        }

        SCREEN_PROTECTOR_KEYWORDS = {
            'positive': ['screen protector', 'tempered glass', 'glass protector', 'screen film'],
            'required': [],
            'negative': ['case', 'charger', 'cable']
        }

        keyword_map = {
            'phone case': PHONE_CASE_KEYWORDS, 'phone_case': PHONE_CASE_KEYWORDS,
            'phone cases': PHONE_CASE_KEYWORDS, 'phone_cases': PHONE_CASE_KEYWORDS,
            'case': PHONE_CASE_KEYWORDS, 'cases': PHONE_CASE_KEYWORDS,
            'cover': PHONE_CASE_KEYWORDS, 'covers': PHONE_CASE_KEYWORDS,
            'charger': CHARGER_KEYWORDS, 'chargers': CHARGER_KEYWORDS,
            'adapter': CHARGER_KEYWORDS, 'adapters': CHARGER_KEYWORDS,
            'cable': CABLE_KEYWORDS, 'cables': CABLE_KEYWORDS,
            'airpods': AUDIO_KEYWORDS, 'airpod': AUDIO_KEYWORDS,
            'earbuds': AUDIO_KEYWORDS, 'earphones': AUDIO_KEYWORDS,
            'headphones': AUDIO_KEYWORDS, 'headphone': AUDIO_KEYWORDS,
            'audio': AUDIO_KEYWORDS, 'buds': AUDIO_KEYWORDS,
            'watch': WATCH_KEYWORDS, 'watches': WATCH_KEYWORDS,
            'smartwatch': WATCH_KEYWORDS, 'smart watch': WATCH_KEYWORDS,
            'apple watch': WATCH_KEYWORDS,
            'phone': PHONE_KEYWORDS, 'phones': PHONE_KEYWORDS,
            'iphone': PHONE_KEYWORDS, 'samsung': PHONE_KEYWORDS,
            'mobile': PHONE_KEYWORDS, 'smartphone': PHONE_KEYWORDS,
            'tablet': TABLET_KEYWORDS, 'tablets': TABLET_KEYWORDS,
            'ipad': TABLET_KEYWORDS,
            'screen protector': SCREEN_PROTECTOR_KEYWORDS,
            'screen protectors': SCREEN_PROTECTOR_KEYWORDS,
            'tempered glass': SCREEN_PROTECTOR_KEYWORDS,
        }

        if category_lower in keyword_map:
            return keyword_map[category_lower].copy()

        words = category_lower.replace('_', ' ').split()
        positive = [w for w in words if len(w) > 2]
        return {
            'positive': positive,
            'required': [],
            'negative': []
        }

    def _fallback_load_all_products(self, search_category: str, keywords_dict: dict) -> List[Dict]:
        """Fallback: fetch all products and use score-based selection."""

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

            return self._select_best_products(all_products, keywords_dict)

        except Exception as e:
            print(f"[ERROR] Fallback error: {str(e)}")
            return []


# ===================================================================
# STANDALONE TEST - run: python services/product_loader.py
# Delete this function when no longer needed
# ===================================================================

def _test():
    import sys, os, json
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    test_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'test', 'test_store_data.json')
    with open(test_file, encoding='utf-8') as f:
        test_data = json.load(f)

    class TestLoader(ProductLoaderMixin):
        """Minimal test class with mocked cross-mixin dependency"""
        def _select_best_products(self, products, keywords_dict):
            return products[:self.max_products]

    t = TestLoader()
    t.max_products = 5
    t.demand_keywords = ['premium', 'popular', 'best seller', 'top rated', 'professional']
    t.penalty_keywords = ['cheap', 'bulk', 'wholesale', 'used', 'refurbished']

    print("=" * 60)
    print("TEST: product_loader.py")
    print("=" * 60)
    print(f"Store: {test_data['store_info']['store_url']}")
    print(f"Fetching category: phone_cases\n")

    products = t.load_ebay_products("phone_cases")

    print(f"\n[RESULT] Loaded {len(products)} products")
    for i, p in enumerate(products[:5], 1):
        title = p.get('title', p.get('name', 'N/A'))
        price = p.get('price', 'N/A')
        print(f"  {i}. {title[:60]} | ${price}")

    print("\n[DONE] product_loader.py test complete")


if __name__ == '__main__':
    _test()
