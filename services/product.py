"""
Product Import Orchestrator
Inherits from all product mixin modules and provides the main import workflow.
"""

import os
import time
from typing import List, Dict

from services.product_loader import ProductLoaderMixin
from services.product_scoring import ProductScoringMixin
from services.product_images import ProductImagesMixin
from services.product_processing import ProductProcessingMixin
from services.product_upload import ProductUploadMixin
from services.product_report import ProductReportMixin


class EbayShopifyImporter(
    ProductLoaderMixin,
    ProductScoringMixin,
    ProductImagesMixin,
    ProductProcessingMixin,
    ProductUploadMixin,
    ProductReportMixin
):
    """
    Import products from API to Shopify.
    All methods are inherited from the mixin modules.
    """

    def __init__(self, shopify_store: str, access_token: str, max_products: int = 10,
                 debug: bool = False, customer_email: str = None):
        self.shopify_store = shopify_store
        self.shopify_headers = {
            "X-Shopify-Access-Token": access_token,
            "Content-Type": "application/json"
        }
        self.shopify_api_version = "2024-01"
        self.shopify_url = f"https://{shopify_store}/admin/api/{self.shopify_api_version}"

        self.max_products = min(max(max_products, 5), 30)
        self.debug = debug
        self.customer_email = customer_email

        self.email_config = {
            'smtp_server': os.environ.get('SMTP_SERVER', 'smtp.gmail.com'),
            'smtp_port': int(os.environ.get('SMTP_PORT', 587)),
            'smtp_username': os.environ.get('SMTP_USERNAME', ''),
            'smtp_password': os.environ.get('SMTP_PASSWORD', ''),
            'from_email': os.environ.get('FROM_EMAIL', 'noreply@yourstore.com'),
            'from_name': os.environ.get('FROM_NAME', 'Product Import System')
        }

        self.demand_keywords = [
            'best seller', 'bestseller', 'popular', 'hot', 'trending',
            'top rated', 'top-rated', 'premium', 'professional', 'pro',
            'original', 'genuine', 'official', 'authentic', 'new arrival',
            'best quality', 'high quality', 'top quality', '5 star', '4.9'
        ]

        self.penalty_keywords = [
            'cheap', 'wholesale', 'bulk', 'lot of', 'bundle',
            'used', 'refurbished', 'replica', 'copy', 'fake',
            'unknown', 'generic', 'unbranded', 'no brand'
        ]

    def import_products(self, search_category: str = "phone case",
                        generate_report: bool = True,
                        send_email: bool = True,
                        recipient_email: str = None) -> Dict:
        """
        Main workflow: fetch → score → enhance → upload → report → email
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

        # Step 1: Load products
        products = self.load_ebay_products(search_category=search_category)

        if not products:
            print("\n[ERROR] No products to import")
            return {"success": False, "message": "No products found in API", "uploaded": 0, "failed": 0}

        print(f"[OK] Ready to upload {len(products)} products\n")

        # Step 2: Enhance images
        print("\n" + "=" * 70)
        print("STEP: ENHANCING IMAGES FROM API")
        print("=" * 70 + "\n")
        self._enhance_products_batch(products)
        print(f"\n[INFO] Waiting 5 seconds for image processing...")
        time.sleep(5)
        print("[OK] Image enhancement complete\n")

        # Step 3: Generate CSV report before upload
        report_file = ''
        if generate_report:
            print("\nSTEP: Generating CSV report...")
            try:
                report_file = self.generate_csv_report(products)
                if not report_file:
                    print("[WARN] CSV report generation failed — email will send without attachment")
            except Exception as exc:
                print(f"[WARN] CSV report error: {exc} — continuing without report")

        # Step 4: Upload products
        success = 0
        failed = 0
        uploaded_products = []

        for i, product in enumerate(products, 1):
            print(f"[{i}/{len(products)}] {product['title'][:50]}...")

            # Try to get enhanced images from server (multiple high-res images)
            item_id = str(product.get('item_id') or product.get('id') or product.get('itemId', ''))
            if item_id:
                enhanced = self._get_enhanced_product_images(item_id)
                if enhanced:
                    product['images'] = enhanced

            # Fallback: extract from product data if no enhanced images
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

            if i < len(products):
                time.sleep(1.5)

        # Step 5: Upload hero banner image
        print("\n" + "=" * 70)
        print("STEP: Uploading Hero Banner")
        print("=" * 70 + "\n")
        hero_ok = self.upload_hero_image()
        if hero_ok:
            print("[OK] Hero image uploaded\n")
        else:
            print("[WARN] Hero image upload failed — continuing\n")

        # Step 6: Send email report
        email_sent = False
        if send_email:
            print("\nSTEP: Sending email report...")
            try:
                email_sent = self.send_report_email(
                    csv_file=report_file,
                    products=uploaded_products if uploaded_products else products,
                    recipient_email=recipient_email
                )
                if email_sent:
                    print(f"[OK] Email sent successfully to {recipient_email or self.customer_email}")
                else:
                    print("[WARN] Email not sent — check SMTP config or recipient email")
            except Exception as exc:
                print(f"[ERROR] Email sending failed: {exc}")

        # Summary
        print("\n" + "=" * 70)
        print("IMPORT SUMMARY")
        print("=" * 70)
        print(f"Successful: {success} products")
        print(f"Failed: {failed} products")
        if products:
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


# ===================================================================
# Wrapper Class for compatibility with app.py
# ===================================================================

class ProductImporter:
    """Wrapper class for compatibility with app.py"""

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
        self._email_config = {
            'smtp_server': smtp_server,
            'smtp_port': smtp_port,
            'smtp_username': smtp_username,
            'smtp_password': smtp_password,
            'from_email': from_email,
            'from_name': from_name
        }
        print("[OK] Email configuration saved")
