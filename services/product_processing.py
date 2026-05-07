"""
Product Processing Mixin - Parsing, Titles & Descriptions
Handles product parsing, title rewriting, description generation, and data extraction.
"""

import re
import hashlib
from typing import Dict, List, Optional, Union


class ProductProcessingMixin:
    """Mixin for product processing and parsing"""

    def _extract_price(self, product: Dict) -> Optional[float]:
        """Extract price from product"""
        price_fields = ['price', 'current_price', 'selling_price', 'sale_price',
                       'ebay_price', 'cost', 'amount']

        for field in price_fields:
            if field in product:
                price = self._clean_price_value(product[field])
                if price and price > 0:
                    return round(price * 1.4, 2)

        return 19.99

    def _clean_price_value(self, value: Union[str, int, float, Dict, None]) -> Optional[float]:
        """Clean price value"""
        if value is None:
            return None

        try:
            if isinstance(value, dict):
                if 'value' in value:
                    return float(value['value'])
                elif 'amount' in value:
                    return float(value['amount'])

            if isinstance(value, str):
                cleaned = ''.join(c for c in value if c.isdigit() or c == '.')
                if cleaned:
                    return float(cleaned)

            return float(value)

        except:
            return None

    def _parse_product(self, item: Dict) -> Optional[Dict]:
        """Parse and prepare product for upload"""
        product = item['product']

        title = product.get('title', product.get('name', ''))
        price = self._extract_price(product)
        images = self._extract_images(product)

        if not title or not price:
            return None

        rewritten_title = self._rewrite_title(title)
        description = self._create_professional_description(product, title, price)
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
        """
        Smart title rewriting - creates catchy, clear, and simple product titles.
        Example:
        Input: "Cheap Factory Hot Sale Shockproof Silicone Case For iPhone 15 Pro Max Wholesale"
        Output: "Shockproof Silicone Case for iPhone 15 Pro Max"
        """
        title_lower = title.lower()

        # 1. EXTRACT BRAND/MODEL
        brand_patterns = {
            'iPhone 16 Pro Max': r'iphone\s*16\s*pro\s*max',
            'iPhone 16 Pro': r'iphone\s*16\s*pro(?!\s*max)',
            'iPhone 16 Plus': r'iphone\s*16\s*plus',
            'iPhone 16': r'iphone\s*16(?!\s*(pro|plus|max))',
            'iPhone 15 Pro Max': r'iphone\s*15\s*pro\s*max',
            'iPhone 15 Pro': r'iphone\s*15\s*pro(?!\s*max)',
            'iPhone 15 Plus': r'iphone\s*15\s*plus',
            'iPhone 15': r'iphone\s*15(?!\s*(pro|plus|max))',
            'iPhone 14 Pro Max': r'iphone\s*14\s*pro\s*max',
            'iPhone 14 Pro': r'iphone\s*14\s*pro(?!\s*max)',
            'iPhone 14 Plus': r'iphone\s*14\s*plus',
            'iPhone 14': r'iphone\s*14(?!\s*(pro|plus|max))',
            'iPhone 13 Pro Max': r'iphone\s*13\s*pro\s*max',
            'iPhone 13 Pro': r'iphone\s*13\s*pro(?!\s*max)',
            'iPhone 13': r'iphone\s*13(?!\s*(pro|mini|max))',
            'iPhone 12 Pro Max': r'iphone\s*12\s*pro\s*max',
            'iPhone 12 Pro': r'iphone\s*12\s*pro(?!\s*max)',
            'iPhone 12': r'iphone\s*12(?!\s*(pro|mini|max))',
            'iPhone SE': r'iphone\s*se',
            'iPhone': r'iphone(?!\s*\d)',
            'Galaxy S24 Ultra': r'galaxy\s*s24\s*ultra',
            'Galaxy S24+': r'galaxy\s*s24\s*(\+|plus)',
            'Galaxy S24': r'galaxy\s*s24(?!\s*(ultra|\+|plus))',
            'Galaxy S23 Ultra': r'galaxy\s*s23\s*ultra',
            'Galaxy S23+': r'galaxy\s*s23\s*(\+|plus)',
            'Galaxy S23': r'galaxy\s*s23(?!\s*(ultra|\+|plus))',
            'Galaxy S22': r'galaxy\s*s22',
            'Galaxy S21': r'galaxy\s*s21',
            'Galaxy A54': r'galaxy\s*a54',
            'Galaxy A53': r'galaxy\s*a53',
            'Galaxy A34': r'galaxy\s*a34',
            'Galaxy Z Fold': r'galaxy\s*z\s*fold',
            'Galaxy Z Flip': r'galaxy\s*z\s*flip',
            'Galaxy Note': r'galaxy\s*note',
            'Samsung Galaxy': r'samsung\s*galaxy',
            'Samsung': r'samsung(?!\s*galaxy)',
            'Google Pixel': r'(google\s*)?pixel\s*\d*',
            'OnePlus': r'oneplus\s*\d*',
            'Xiaomi': r'xiaomi|redmi|poco',
            'Huawei': r'huawei',
            'Motorola': r'motorola|moto\s*[gez]',
            'OPPO': r'oppo',
            'Vivo': r'vivo',
            'Nokia': r'nokia',
        }

        detected_brand = None
        for brand_name, pattern in brand_patterns.items():
            if re.search(pattern, title_lower):
                detected_brand = brand_name
                break

        # 2. EXTRACT PRODUCT TYPE
        product_types = {
            'Wallet Case': r'wallet\s*(case|cover)|flip\s*cover|leather\s*wallet',
            'Clear Case': r'clear\s*(case|cover)|transparent\s*(case|cover)',
            'Silicone Case': r'silicone\s*(case|cover)|soft\s*case',
            'Hard Case': r'hard\s*(case|cover)|pc\s*case|plastic\s*case',
            'Leather Case': r'leather\s*(case|cover)',
            'Hybrid Case': r'hybrid\s*(case|cover)',
            'Armor Case': r'armor\s*(case|cover)|rugged\s*(case|cover)',
            'Slim Case': r'slim\s*(case|cover)|thin\s*(case|cover)',
            'Protective Case': r'protective\s*(case|cover)|protection\s*(case|cover)',
            'Phone Case': r'phone\s*(case|cover)|mobile\s*(case|cover)|cell\s*phone\s*(case|cover)',
            'Case': r'\b(case|cover|shell|bumper)\b',
            'Fast Charger': r'fast\s*charger|quick\s*charge|pd\s*charger',
            'Wireless Charger': r'wireless\s*charger|qi\s*charger',
            'Charger': r'charger|adapter|charging',
            'USB-C Cable': r'usb[\s-]?c\s*cable|type[\s-]?c\s*cable',
            'Lightning Cable': r'lightning\s*cable',
            'Cable': r'cable|cord',
            'Screen Protector': r'screen\s*protector|tempered\s*glass|glass\s*protector',
            'AirPods Case': r'airpods?\s*case',
            'AirPods': r'airpods?|earbuds|tws',
            'Headphones': r'headphones?|headset|earphones?',
            'Power Bank': r'power\s*bank|portable\s*charger|battery\s*pack',
            'Watch Band': r'watch\s*(band|strap)|smartwatch\s*(band|strap)',
            'Phone Stand': r'phone\s*(stand|holder|mount|grip)',
        }

        detected_type = None
        for type_name, pattern in product_types.items():
            if re.search(pattern, title_lower):
                detected_type = type_name
                break

        if not detected_type:
            detected_type = 'Accessory'

        # 3. EXTRACT KEY FEATURES (max 2)
        features = {
            'Shockproof': r'shockproof|shock\s*proof|anti[\s-]?shock|drop\s*proof',
            'Waterproof': r'waterproof|water[\s-]?resistant|ip\d+',
            'Slim': r'\bslim\b|ultra[\s-]?thin|thin\b',
            'Clear': r'\bclear\b|transparent',
            'Magnetic': r'magnetic|magsafe|mag\s*safe',
            'Premium': r'premium|luxury|high[\s-]?quality',
            'Leather': r'\bleather\b|pu\s*leather',
            'Soft': r'\bsoft\b|flexible|tpu',
            'Hard': r'\bhard\b|rigid|pc\b',
            'Matte': r'\bmatte\b|frosted',
            'Glossy': r'\bglossy\b|shiny',
            'Rugged': r'\brugged\b|heavy[\s-]?duty|military',
            'Wireless': r'\bwireless\b|bluetooth',
            'Fast': r'\bfast\b|quick|rapid',
            'Portable': r'\bportable\b|compact|mini',
            'Original': r'\boriginal\b|genuine|authentic',
        }

        detected_features = []
        for feature_name, pattern in features.items():
            if re.search(pattern, title_lower):
                detected_features.append(feature_name)
                if len(detected_features) >= 2:
                    break

        # 4. BUILD CLEAN TITLE
        title_parts = []

        if detected_features:
            title_parts.extend(detected_features)

        title_parts.append(detected_type)

        if detected_brand:
            title_parts.append(f"for {detected_brand}")

        new_title = ' '.join(title_parts)

        # 5. FINAL CLEANUP
        new_title = ' '.join(new_title.split())

        new_title = new_title.strip()
        if new_title:
            words = new_title.split()
            words = [w.capitalize() if w.lower() != 'for' else 'for' for w in words]
            new_title = ' '.join(words)

        if len(new_title) < 10:
            unwanted = ['cheap', 'china', 'wholesale', 'dropship', 'factory',
                       'hot sale', 'new arrival', 'free shipping', 'best seller',
                       'fast delivery', 'low price', 'high quality', 'top seller']
            clean_title = title
            for word in unwanted:
                clean_title = re.sub(rf'\b{word}\b', '', clean_title, flags=re.IGNORECASE)
            clean_title = ' '.join(clean_title.split())
            if len(clean_title) > len(new_title):
                new_title = clean_title.strip()
                if new_title:
                    new_title = new_title[0].upper() + new_title[1:]

        return new_title[:255]

    def _detect_product_type(self, title: str) -> str:
        """Detect product type from title"""
        title_lower = title.lower()

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
        """Create a professional, minimal, black & white product description"""

        product_type = self._detect_product_type(title)

        specs = self._extract_specifications(product, product_type)
        compatibility = self._extract_compatibility(title, product)

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
        if title.isupper():
            title = title.title()

        remove_words = ['NEW', 'HOT', 'SALE', '!!!', '---', '***', 'BEST', 'TOP']
        for word in remove_words:
            title = title.replace(word, '')

        title = ' '.join(title.split())
        return title[:100]

    def _extract_specifications(self, product: Dict, product_type: str) -> Dict:
        """Extract product specifications from available data"""
        specs = {}

        spec_fields = ['specifications', 'specs', 'attributes', 'details', 'properties']

        for field in spec_fields:
            if field in product and isinstance(product[field], dict):
                for key, value in product[field].items():
                    if value and str(value).strip():
                        specs[key.replace('_', ' ').title()] = str(value)

        if 'material' in product:
            specs['Material'] = str(product['material'])
        if 'color' in product:
            specs['Color'] = str(product['color'])
        if 'weight' in product:
            specs['Weight'] = str(product['weight'])
        if 'dimensions' in product:
            specs['Dimensions'] = str(product['dimensions'])

        return dict(list(specs.items())[:6])

    def _extract_compatibility(self, title: str, product: Dict) -> str:
        """Extract device compatibility from title and product data"""
        title_lower = title.lower()
        compatibility = []

        iphone_models = ['iphone 16', 'iphone 15', 'iphone 14', 'iphone 13', 'iphone 12', 'iphone 11',
                        'iphone se', 'iphone x', 'iphone xs', 'iphone xr', 'iphone pro', 'iphone plus', 'iphone max']
        for model in iphone_models:
            if model in title_lower:
                compatibility.append(model.replace('iphone', 'iPhone'))

        samsung_patterns = [
            ('galaxy s24', 'Galaxy S24'), ('galaxy s23', 'Galaxy S23'), ('galaxy s22', 'Galaxy S22'),
            ('galaxy a54', 'Galaxy A54'), ('galaxy a53', 'Galaxy A53'), ('galaxy note', 'Galaxy Note'),
            ('galaxy z fold', 'Galaxy Z Fold'), ('galaxy z flip', 'Galaxy Z Flip')
        ]
        for pattern, display in samsung_patterns:
            if pattern in title_lower:
                compatibility.append(f'Samsung {display}')

        if 'compatibility' in product:
            compat_data = product['compatibility']
            if isinstance(compat_data, str):
                return compat_data
            elif isinstance(compat_data, list):
                compatibility.extend(compat_data)

        if compatibility:
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


# ===================================================================
# STANDALONE TEST - run: python services/product_processing.py
# Delete this function when no longer needed
# ===================================================================

def _test():
    import sys, os, json
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from services.product_images import ProductImagesMixin

    test_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'test', 'test_store_data.json')
    with open(test_file, encoding='utf-8') as f:
        test_data = json.load(f)

    class TestProcessing(ProductProcessingMixin, ProductImagesMixin):
        pass

    t = TestProcessing()
    t.debug = False

    print("=" * 60)
    print("TEST: product_processing.py")
    print("=" * 60)

    for i, raw in enumerate(test_data['raw_products'], 1):
        original = raw.get('title', '')
        rewritten = t._rewrite_title(original)
        print(f"\nProduct {i}:")
        print(f"  Original : {original[:70]}")
        print(f"  Rewritten: {rewritten[:70]}")

        parsed = t._parse_product({'product': raw})
        if parsed:
            print(f"  Price    : ${parsed.get('price')}")
            print(f"  SKU      : {parsed.get('sku')}")
            print(f"  Images   : {len(parsed.get('images', []))}")
        else:
            print("  [SKIP] Product filtered out by parser")

    print("\n[DONE] product_processing.py test complete")


if __name__ == '__main__':
    _test()
