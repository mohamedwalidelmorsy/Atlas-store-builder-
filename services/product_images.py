"""
Product Images Mixin - Image Extraction & Enhancement
Handles image extraction, validation, enhancement, and quality sorting.
"""

import re
import json
import requests
from typing import List, Dict


class ProductImagesMixin:
    """Mixin for image extraction and enhancement"""

    def _request_enhanced_images(self, item_ids: List[str]) -> Dict:
        """Request enhanced images for products from server API"""
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
        """Fetch enhanced images for a single product from API"""
        api_url = f"http://199.192.25.89:5000/api/enhanced/{item_id}"

        try:
            response = requests.get(api_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('data', {}).get('enhanced'):
                    images_data = data['data'].get('images', [])
                    return [img['url'] for img in images_data if 'url' in img]
        except Exception as e:
            if self.debug:
                print(f"[WARN] Could not fetch enhanced images for {item_id}: {e}")

        return []

    def _enhance_products_batch(self, products: List[Dict]) -> None:
        """Enhance a batch of products at once"""
        item_ids = []

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

    def _extract_images(self, product: Dict, scoring_mode: bool = False) -> List[str]:
        """Enhanced image extraction with API support and deep recursive search"""

        images = set()
        debug = self.debug

        if debug:
            print(f"\n[DEBUG] Extracting images from: {product.get('title', 'Unknown')[:50]}")

        # STEP 1: Direct field extraction
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

        # STEP 2: Deep recursive search
        deep_images = self._deep_extract_images(product, visited=set(), depth=0, max_depth=5)
        images.update(deep_images)

        if debug:
            print(f"[DEBUG] After deep search: {len(images)} images")

        # STEP 3: Regex fallback
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

        # STEP 4: Clean, validate, and optimize
        valid_images = []
        seen_normalized = set()

        for img in images:
            if not img or len(img) < 10:
                continue

            img = self._upgrade_to_high_res(img)

            normalized = self._normalize_url_for_dedup(img)
            if normalized in seen_normalized:
                continue
            seen_normalized.add(normalized)

            if self._is_valid_image_url(img):
                valid_images.append(img)

        if debug:
            print(f"[DEBUG] Final validated: {len(valid_images)} images")

        valid_images = self._sort_by_quality(valid_images)

        # STEP 5: Fetch from URL if insufficient (skip during scoring_mode)
        if len(valid_images) < 3 and not scoring_mode:
            product_url = None
            url_fields = ['url', 'link', 'product_url', 'productUrl', 'itemUrl',
                         'item_url', 'href', 'viewItemURL', 'ebay_url', 'source_url']

            for field in url_fields:
                if field in product and isinstance(product[field], str):
                    potential_url = product[field].strip()
                    if potential_url.startswith('http'):
                        product_url = potential_url
                        break

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

                fetched_images = self._fetch_images_from_url(product_url)

                if fetched_images:
                    if debug:
                        print(f"[DEBUG] Got {len(fetched_images)} images from URL")

                    existing_normalized = {self._normalize_url_for_dedup(img) for img in valid_images}

                    for img in fetched_images:
                        normalized = self._normalize_url_for_dedup(img)
                        if normalized not in existing_normalized:
                            valid_images.append(img)
                            existing_normalized.add(normalized)

                    valid_images = self._sort_by_quality(valid_images)

                    if debug:
                        print(f"[DEBUG] Total images after URL fetch: {len(valid_images)}")

        # STEP 6: Final validation and return
        if debug:
            print(f"[DEBUG] Final image count: {len(valid_images)}")

        if not valid_images:
            return ['https://via.placeholder.com/800x800/f5f5f5/333333?text=Image+Not+Available']

        return valid_images[:10]

    def _fetch_images_from_url(self, url: str) -> List[str]:
        """Fetch product images directly from the product page URL"""
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

            # Pattern 2: eBay medium-quality images
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
                img = self._clean_image_url(img)
                if not img:
                    continue

                img = self._upgrade_to_high_res(img)

                normalized = self._normalize_url_for_dedup(img)
                if normalized in seen_normalized:
                    continue
                seen_normalized.add(normalized)

                if self._is_valid_image_url(img):
                    unique_images.append(img)

            if self.debug:
                print(f"[DEBUG] Fetched {len(unique_images)} unique images from URL")

            return unique_images[:20]

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

    def _extract_from_value(self, value, debug: bool = False, source: str = "") -> set:
        """Extract image URLs from any value type"""

        results = set()

        if value is None:
            return results

        if isinstance(value, str):
            cleaned = self._clean_image_url(value.strip())
            if cleaned and self._is_valid_image_url(cleaned):
                results.add(cleaned)
                if debug:
                    print(f"[DEBUG] {source} string: {cleaned[:60]}")

        elif isinstance(value, list):
            for item in value:
                results.update(self._extract_from_value(item, debug, f"{source}[list]"))

        elif isinstance(value, dict):
            for key in ['url', 'src', 'href', 'link', 'imageUrl', 'image_url', 'URL', 'source']:
                if key in value:
                    results.update(self._extract_from_value(value[key], debug, f"{source}[{key}]"))

            for k, v in value.items():
                if any(word in k.lower() for word in ['image', 'img', 'photo', 'picture', 'url', 'src']):
                    results.update(self._extract_from_value(v, debug, f"{source}[{k}]"))

        return results

    def _deep_extract_images(self, obj, visited: set, depth: int, max_depth: int) -> set:
        """Recursively extract all image URLs from nested structures"""

        results = set()

        if depth >= max_depth:
            return results

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
                if any(word in key.lower() for word in ['image', 'img', 'photo', 'picture', 'gallery', 'pic', 'media', 'thumb']):
                    results.update(self._extract_from_value(value, self.debug, f"deep:{key}"))

                results.update(self._deep_extract_images(value, visited, depth + 1, max_depth))

        return results

    def _is_valid_image_url(self, url: str) -> bool:
        """Validate that a URL is likely a valid image URL"""

        if not url or len(url) < 15:
            return False

        if not url.startswith(('http://', 'https://')):
            return False

        url_lower = url.lower()

        exclusion_patterns = [
            'pixel', 'tracking', 'beacon', 'spacer', 'blank',
            '1x1', '1px', 'transparent', 'icon', 'favicon',
            'logo', 'badge', 'button', 'sprite', 'loading',
            'placeholder', 'spinner', 'ajax', 'analytics'
        ]

        for pattern in exclusion_patterns:
            if pattern in url_lower:
                return False

        image_indicators = [
            '.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff',
            'ebayimg.com', 'ebaystatic.com',
            'alicdn.com', 'aliexpress.com/item_pic',
            'images-amazon.com', 'ssl-images-amazon.com', 'm.media-amazon.com',
            'cdn.shopify.com', 'shopify.com/s/files',
            'cloudinary.com', 'imgix.net', 'cloudfront.net',
            'i.imgur.com', 'images.unsplash.com',
            '/images/', '/img/', '/photos/', '/pictures/', '/gallery/',
            'image.', 'img.', 'photo.', 'pic.',
            '/product-images/', '/product_images/', '/product/',
            'etsystatic.com', 'wixmp.com'
        ]

        has_indicator = any(indicator in url_lower for indicator in image_indicators)

        if not has_indicator:
            return False

        if len(url) > 2000:
            return False

        return True

    def _verify_image_accessible(self, url: str, timeout: int = 5) -> bool:
        """Verify that an image URL is actually accessible"""
        if not url or not url.startswith('http'):
            return False

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.head(url, timeout=timeout, headers=headers, allow_redirects=True)

            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '').lower()
                if 'image' in content_type:
                    return True

                if any(url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                    return True

            return False

        except Exception:
            return False

    def _normalize_url_for_dedup(self, url: str) -> str:
        """Normalize URL for deduplication comparison"""

        normalized = url.lower()

        normalized = re.sub(r's-l\d+', 's-l', normalized)
        normalized = re.sub(r'\$_\d+', '$_', normalized)

        if '?' in normalized:
            normalized = normalized.split('?')[0]

        return normalized

    def _upgrade_to_high_res(self, url: str) -> str:
        """Upgrade image URL to highest available resolution"""
        if not url:
            return url

        # eBay Image Upgrades
        if 'ebayimg.com' in url:
            size_patterns = [
                'e-l64', 's-l64', 's-l96', 's-l140', 's-l225', 's-l300',
                's-l400', 's-l500', 's-l800', 's-l1200'
            ]
            for pattern in size_patterns:
                if pattern in url:
                    url = url.replace(pattern, 's-l1600')
                    break

            if '/thumbs/images/' in url:
                url = url.replace('/thumbs/images/', '/images/')

            url = re.sub(r'\$_\d+\.', '$_57.', url)
            url = re.sub(r'\$_[A-Z0-9]+\.', '$_57.', url)

            if not any(url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']):
                ext_match = re.search(r'\.(jpg|jpeg|png|webp|gif)', url, re.IGNORECASE)
                if ext_match:
                    ext_pos = ext_match.end()
                    url = url[:ext_pos]

        # AliExpress Image Upgrades
        elif 'alicdn.com' in url or 'aliexpress' in url:
            url = re.sub(r'_\d+x\d+\.', '.', url)
            url = re.sub(r'\.jpg_\d+x\d+\.jpg', '.jpg', url)
            url = re.sub(r'\.jpg\.webp$', '.jpg', url)
            url = re.sub(r'_Q\d+\.jpg', '.jpg', url)

        # Amazon Image Upgrades
        elif 'amazon' in url or 'ssl-images-amazon' in url:
            url = re.sub(r'\._[A-Z]{2}\d+_\.', '.', url)
            url = re.sub(r'\._[A-Z]+_\.', '.', url)

        # Shopify CDN Image Upgrades
        elif 'shopify.com' in url or 'cdn.shopify' in url:
            url = re.sub(r'_\d+x\d+\.', '.', url)
            url = re.sub(r'_(small|medium|large|grande|master)\.', '.', url, flags=re.IGNORECASE)

        # Generic Query Parameter Cleanup
        if '?' in url:
            base_url = url.split('?')[0]
            if any(base_url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']):
                url = base_url

        return url

    def _sort_by_quality(self, images: List[str]) -> List[str]:
        """Sort images by quality indicators"""

        def quality_score(url: str) -> int:
            score = 0
            url_lower = url.lower()

            high_res_patterns = [
                's-l1600', 's-l1200', '_1600', '_1200', '_1024',
                'large', 'full', 'original', 'master', 'zoom'
            ]
            for pattern in high_res_patterns:
                if pattern in url_lower:
                    score += 100
                    break

            med_res_patterns = ['s-l800', 's-l500', '_800', '_500', 'medium']
            for pattern in med_res_patterns:
                if pattern in url_lower:
                    score += 50
                    break

            reliable_hosts = [
                ('ebayimg.com', 40), ('alicdn.com', 35), ('amazon', 35),
                ('shopify.com', 30), ('cloudinary.com', 30), ('imgix.net', 30),
                ('etsystatic.com', 30), ('cloudfront.net', 25),
            ]
            for host, host_score in reliable_hosts:
                if host in url_lower:
                    score += host_score
                    break

            main_patterns = [
                'main', 'primary', 'hero', 'featured',
                '_1.', '_01.', '-1.', '-01.', '/1.', '/01.',
                'front', 'cover'
            ]
            for pattern in main_patterns:
                if pattern in url_lower:
                    score += 20
                    break

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

            if len(url) > 500:
                score -= 20

            return score

        return sorted(images, key=quality_score, reverse=True)

    def _clean_image_url(self, url: str) -> str:
        """Clean and improve image URL"""
        if not url:
            return ''

        url = url.strip()
        url = url.replace('\\/', '/')
        url = url.replace('\\"', '')
        url = url.rstrip('"\'>,;)}]')

        if url.count('http') > 1:
            idx = url.rfind('http')
            url = url[idx:]

        return url


# ===================================================================
# STANDALONE TEST - run: python services/product_images.py
# Delete this function when no longer needed
# ===================================================================

def _test():
    import sys, os, json
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    test_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'test', 'test_store_data.json')
    with open(test_file, encoding='utf-8') as f:
        test_data = json.load(f)

    class TestImages(ProductImagesMixin):
        pass

    t = TestImages()
    t.debug = True

    print("=" * 60)
    print("TEST: product_images.py")
    print("=" * 60)

    for i, raw in enumerate(test_data['raw_products'], 1):
        title = raw.get('title', 'N/A')
        print(f"\nProduct {i}: {title[:55]}")
        images = t._extract_images(raw)
        print(f"  Extracted {len(images)} image(s)")
        for img in images:
            print(f"  - {img[:80]}")

    print("\n[DONE] product_images.py test complete")


if __name__ == '__main__':
    _test()
