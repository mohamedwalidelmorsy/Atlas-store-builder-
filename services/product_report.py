"""
Product Report Mixin - CSV Reports & Email
Handles CSV report generation, Google Sheets data formatting, and email sending.
"""

import os
import csv
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Dict
from datetime import datetime


class ProductReportMixin:
    """Mixin for report generation and email sending"""

    def generate_csv_report(self, products: List[Dict], filename: str = None) -> str:
        """Generate a CSV report of selected products for manual review"""

        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            reports_dir = os.path.join("data", "reports")
            os.makedirs(reports_dir, exist_ok=True)
            filename = os.path.join(reports_dir, f"product_import_report_{timestamp}.csv")

        headers = [
            'Product Title', 'Original Title', 'Shopify Price', 'Source Price',
            'Profit Margin %', 'Product URL', 'Seller Name', 'Seller Rating',
            'Image Count', 'Final Score', 'SKU'
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
        """Generate data formatted for Google Sheets API"""

        headers = [
            'Product Title', 'Original Title', 'Shopify Price', 'Source Price',
            'Profit Margin %', 'Product URL', 'Seller Name', 'Seller Rating',
            'Image Count', 'Final Score', 'SKU', 'Status'
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

    def send_report_email(self, csv_file: str, products: List[Dict], recipient_email: str = None) -> bool:
        """Send the CSV report via email to the customer"""

        to_email = recipient_email or self.customer_email

        if not to_email:
            print("[WARN] No recipient email provided, skipping email send")
            return False

        has_attachment = bool(csv_file and os.path.exists(csv_file))
        if csv_file and not has_attachment:
            print(f"[WARN] CSV file not found — sending email without attachment")

        print(f"\n[INFO] Sending report to: {to_email}")

        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Product Import Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            msg['From'] = f"{self.email_config['from_name']} <{self.email_config['from_email']}>"
            msg['To'] = to_email

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
        .score-high {{ background: #d4edda; color: #155724; }}
        .score-medium {{ background: #fff3cd; color: #856404; }}
        .score-low {{ background: #f8d7da; color: #721c24; }}
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

            for i, p in enumerate(products[:10], 1):
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

            part1 = MIMEText(text_content, 'plain')
            part2 = MIMEText(html_content, 'html')
            msg.attach(part1)
            msg.attach(part2)

            # Attach CSV file (optional — only if file exists)
            if has_attachment:
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

            if not smtp_username or not smtp_password:
                print("[WARN] SMTP credentials not configured")
                print("[INFO] To enable email, set environment variables:")
                print("       SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, FROM_EMAIL")

                email_backup_file = csv_file.replace('.csv', '_email.html')
                with open(email_backup_file, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                print(f"[INFO] Email content saved to: {email_backup_file}")
                return False

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
        """Configure email settings programmatically"""
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


# ===================================================================
# STANDALONE TEST - run: python services/product_report.py
# Reads SMTP settings from .env — make sure .env is configured
# Delete this function when no longer needed
# ===================================================================

def _test():
    import sys, os, json
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

    test_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'test', 'test_store_data.json')
    with open(test_file, encoding='utf-8') as f:
        test_data = json.load(f)

    store_info = test_data['store_info']
    store_host = store_info['store_url'].replace('https://', '').replace('http://', '').split('/')[0]

    class TestReport(ProductReportMixin):
        pass

    t = TestReport()
    t.shopify_store = store_host
    t.customer_email = store_info['customer_email']
    t.email_config = {
        'smtp_server': os.environ.get('SMTP_SERVER', 'smtp.gmail.com'),
        'smtp_port': int(os.environ.get('SMTP_PORT', 587)),
        'smtp_username': os.environ.get('SMTP_USERNAME', ''),
        'smtp_password': os.environ.get('SMTP_PASSWORD', ''),
        'from_email': os.environ.get('FROM_EMAIL', ''),
        'from_name': os.environ.get('FROM_NAME', 'Test System')
    }

    # Minimal products list for report testing
    products = [
        {
            'title': 'Magnetic Leather Case for iPhone 15',
            'original_title': 'Magnetic Leather Phone Case for Iphone 15...',
            'price': '27.99',
            'ebay_price': 19.99,
            'profit_margin': 40.0,
            'product_url': 'https://example.com/p1',
            'sku': 'IP15-MAG-LEA',
            'images': ['https://example.com/img1.jpg'],
            'final_score': 85,
            'seller_info': {'seller_name': 'TestSeller', 'seller_rating': '99%'}
        },
        {
            'title': 'Shockproof Rugged Case for Samsung Galaxy',
            'original_title': 'Shockproof Rugged Phone Case for Samsung Galaxy...',
            'price': '22.39',
            'ebay_price': 15.99,
            'profit_margin': 40.0,
            'product_url': 'https://example.com/p2',
            'sku': 'SAM-SHOCK-001',
            'images': [],
            'final_score': 72,
            'seller_info': {'seller_name': 'TestSeller2', 'seller_rating': '97%'}
        }
    ]

    print("=" * 60)
    print("TEST: product_report.py")
    print("=" * 60)
    print(f"Store  : {t.shopify_store}")
    print(f"Email  : {t.customer_email}")
    print(f"SMTP   : {t.email_config['smtp_server']} (user: {t.email_config['smtp_username'] or 'NOT SET'})")
    print()

    # Test CSV generation
    csv_file = t.generate_csv_report(products)
    print(f"[RESULT] CSV: {csv_file}")

    # Test email sending
    print("\nSending test email...")
    sent = t.send_report_email(csv_file=csv_file, products=products)
    print(f"[RESULT] Email: {'SENT' if sent else 'FAILED (check SMTP config in .env)'}")

    print("\n[DONE] product_report.py test complete")


if __name__ == '__main__':
    _test()
