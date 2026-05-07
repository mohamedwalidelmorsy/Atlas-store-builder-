"""
Product Scoring Mixin - Scoring & Filtering
Handles product relevance scoring, quality scoring, filtering, and selection.
"""

import random
from typing import List, Dict, Tuple


class ProductScoringMixin:
    """Mixin for product scoring and filtering"""

    def _calculate_relevance_score(self, product: Dict, keywords_dict: dict, relaxed_mode: bool = False) -> Tuple[float, Dict]:
        """
        Calculate relevance score for a product based on category matching.

        SCORING SYSTEM (Ranking > Filtering):
        - product_type == "case"  +50 points
        - product_type == "accessory"  +20 points
        - product_type == "other"  +5 points
        - Title contains case/cover/shell  +30 points each (max +60)
        - Title contains phone brands/models  +20 points each (max +40)
        - Required keyword match  +25 points
        - Positive keyword match  +15 points each (max +45)
        - Negative keywords  -15 points each (max -45 penalty)
        """

        title = product.get('title', product.get('name', '')).lower()
        description = product.get('description', '').lower()
        product_type = product.get('product_type', '').lower()
        check_text = f"{title} {description}"

        score = 0
        breakdown = {
            'product_type': 0,
            'case_keywords': 0,
            'brand_keywords': 0,
            'required': 0,
            'positive': 0,
            'negative': 0
        }

        # 1. PRODUCT TYPE SCORING
        if product_type == 'case':
            breakdown['product_type'] = 50
        elif product_type == 'accessory':
            breakdown['product_type'] = 20
        elif product_type == 'other':
            breakdown['product_type'] = 5

        score += breakdown['product_type']

        # 2. CASE/COVER KEYWORDS IN TITLE
        case_keywords = ['case', 'cover', 'shell', 'phone case', 'mobile case',
                         'protective case', 'back cover', 'flip cover', 'wallet case']
        case_matches = 0
        for kw in case_keywords:
            if kw in title:
                case_matches += 1
                if case_matches >= 2:
                    break
        breakdown['case_keywords'] = min(case_matches * 30, 60)
        score += breakdown['case_keywords']

        # 3. PHONE BRAND/MODEL KEYWORDS
        brand_keywords = [
            'iphone', 'samsung', 'galaxy', 'pixel', 'oneplus', 'xiaomi',
            'redmi', 'huawei', 'oppo', 'vivo', 'motorola', 'nokia',
            'iphone 16', 'iphone 15', 'iphone 14', 'iphone 13', 'iphone 12',
            'galaxy s24', 'galaxy s23', 'galaxy s22', 'galaxy a54', 'galaxy a53'
        ]
        brand_matches = 0
        for brand in brand_keywords:
            if brand in title:
                brand_matches += 1
                if brand_matches >= 2:
                    break
        breakdown['brand_keywords'] = min(brand_matches * 20, 40)
        score += breakdown['brand_keywords']

        # 4. REQUIRED KEYWORDS
        required = keywords_dict.get('required', [])
        if required:
            has_required = any(req.lower() in title for req in required)
            if has_required:
                breakdown['required'] = 25
                score += 25

        # 5. POSITIVE KEYWORDS SCORING
        positive = keywords_dict.get('positive', [])
        if positive:
            positive_matches = sum(1 for pos in positive if pos.lower() in check_text)
            breakdown['positive'] = min(positive_matches * 15, 45)
            score += breakdown['positive']

        # 6. NEGATIVE KEYWORDS PENALTY
        negative = keywords_dict.get('negative', [])
        penalty_multiplier = 0.5 if relaxed_mode else 1.0

        if negative:
            negative_matches = sum(1 for neg in negative if neg.lower() in title)
            penalty = min(negative_matches * 15, 45) * penalty_multiplier
            breakdown['negative'] = -penalty
            score -= penalty

        return max(score, 0), breakdown

    def _apply_minimal_hard_filter(self, products: List[Dict], allowed_types: List[str] = None) -> List[Dict]:
        """Apply MINIMAL hard filter - only reject completely irrelevant products."""
        if allowed_types is None:
            allowed_types = ['case', 'accessory', 'other']

        filtered = []
        rejected_count = 0

        for product in products:
            product_type = product.get('product_type', '').lower()

            if product_type and product_type not in allowed_types:
                rejected_count += 1
                continue

            filtered.append(product)

        if rejected_count > 0:
            print(f"[FILTER] Hard filter rejected {rejected_count} products (wrong product_type)")
            print(f"[FILTER] Allowed types: {allowed_types}")

        return filtered

    def _score_all_products(self, products: List[Dict], keywords_dict: dict, relaxed_mode: bool = False) -> List[Dict]:
        """Score all products combining RELEVANCE score + QUALITY score."""
        if not products:
            return []

        scored_products = []
        print(f"[INFO] Scoring {len(products)} products (relaxed={relaxed_mode})...")
        progress_interval = max(1, len(products) // 10)

        for idx, product in enumerate(products):
            if (idx + 1) % progress_interval == 0:
                print(f"  Progress: {idx + 1}/{len(products)} ({((idx+1)/len(products)*100):.0f}%)")

            title = product.get('title', product.get('name', ''))
            price = self._extract_price(product)
            images = self._extract_images(product, scoring_mode=True)

            if not title or not price or not images:
                continue

            relevance_score, relevance_breakdown = self._calculate_relevance_score(
                product, keywords_dict or {}, relaxed_mode=relaxed_mode
            )

            quality_score, quality_breakdown = self._calculate_product_score_v2(
                product, price, images, keywords_dict
            )

            combined_score = relevance_score + quality_score

            full_breakdown = {
                **quality_breakdown,
                'relevance': relevance_score,
                'relevance_detail': relevance_breakdown
            }

            scored_products.append({
                'product': product,
                'index': idx,
                'score': quality_score,
                'combined_score': combined_score,
                'relevance_score': relevance_score,
                'score_breakdown': full_breakdown,
                'title': title,
                'price': price,
                'images': images
            })

        print(f"[OK] Scored {len(scored_products)} valid products")
        return scored_products

    def _select_best_products(self, products: List[Dict], keywords_dict: dict = None) -> List[Dict]:
        """Select best products using SCORE-BASED RANKING."""

        print(f"\n[INFO] Analyzing {len(products)} products to select best {self.max_products}...")

        # STEP 1: Minimal Hard Filter
        allowed_types = ['case', 'accessory', 'other']
        filtered_products = self._apply_minimal_hard_filter(products, allowed_types)
        print(f"[OK] After minimal hard filter: {len(filtered_products)} products")

        # STEP 2: Score all products
        scored_products = self._score_all_products(filtered_products, keywords_dict, relaxed_mode=False)

        # STEP 3: Smart Fallback
        if len(scored_products) == 0:
            print(f"\n[WARN] No products scored well. Activating SMART FALLBACK...")

            print(f"[FALLBACK 1] Relaxing penalties and rescoring...")
            scored_products = self._score_all_products(filtered_products, keywords_dict, relaxed_mode=True)

            if len(scored_products) == 0:
                print(f"[FALLBACK 2] Expanding allowed product types...")
                expanded_types = ['case', 'accessory', 'other', 'phone', 'charger', 'audio']
                filtered_products = self._apply_minimal_hard_filter(products, expanded_types)
                scored_products = self._score_all_products(filtered_products, keywords_dict, relaxed_mode=True)

            if len(scored_products) == 0:
                print(f"[FALLBACK 3] Using all products with minimal criteria...")
                scored_products = self._score_all_products(products, keywords_dict, relaxed_mode=True)

        # STEP 4: Select top N
        scored_products.sort(key=lambda x: x['combined_score'], reverse=True)
        selected = scored_products[:self.max_products]

        print(f"\n[OK] Selected top {len(selected)} products out of {len(scored_products)} scored")

        if len(selected) == 0:
            print(f"[CRITICAL] Still no products! Using random sample as last resort...")
            sample_size = min(self.max_products, len(products))
            if sample_size > 0:
                random_sample = random.sample(products, sample_size)
                selected = self._score_all_products(random_sample, keywords_dict, relaxed_mode=True)[:self.max_products]

        # Download enhanced images ONLY for selected products
        print(f"\n[INFO] Downloading enhanced images for {len(selected)} selected products...")
        selected_products_list = [item['product'] for item in selected]
        self._enhance_products_batch(selected_products_list)

        # Re-extract images after enhancement
        for item in selected:
            item['images'] = self._extract_images(item['product'])

        print(f"\n{'='*70}")
        print(f"TOP {len(selected)} PRODUCTS (Ranked by Combined Score)")
        print(f"{'='*70}")

        for i, item in enumerate(selected, 1):
            print(f"{i}. {item['title'][:55]}...")
            combined = item.get('combined_score', item.get('score', 0))
            relevance = item.get('relevance_score', 0)
            quality = item.get('score', 0)
            print(f"   Price: ${item['price']:.2f} | Combined: {combined:.0f} (Relevance: {relevance:.0f} + Quality: {quality:.0f}) | Images: {len(item['images'])}")

            breakdown = item.get('score_breakdown', {})
            rel_detail = breakdown.get('relevance_detail', {})
            if rel_detail:
                print(f"   [Type:{rel_detail.get('product_type', 0):.0f} Case:{rel_detail.get('case_keywords', 0):.0f} Brand:{rel_detail.get('brand_keywords', 0):.0f} Req:{rel_detail.get('required', 0):.0f}]")

        print(f"{'='*70}\n")

        # Convert to final format
        final_products = []
        for item in selected:
            parsed = self._parse_product(item)
            if parsed:
                parsed['final_score'] = item.get('combined_score', item.get('score', 0))
                parsed['relevance_score'] = item.get('relevance_score', 0)
                parsed['quality_score'] = item.get('score', 0)
                parsed['score_breakdown'] = item.get('score_breakdown', {})
                final_products.append(parsed)

        # Final safety check
        if not final_products and products:
            print(f"[CRITICAL] Parsed 0 products! Creating minimal fallback...")
            sample = random.sample(products, min(self.max_products, len(products)))
            for product in sample:
                title = product.get('title', product.get('name', ''))
                price = self._extract_price(product)
                images = self._extract_images(product)
                if title and price and images:
                    final_products.append({
                        'title': title,
                        'price': price,
                        'images': images,
                        'final_score': 0,
                        'relevance_score': 0,
                        'quality_score': 0,
                        'score_breakdown': {},
                        'product': product
                    })
                if len(final_products) >= self.max_products:
                    break

        return final_products

    def _calculate_product_score_v2(self, product: Dict, price: float, images: List[str], keywords_dict: dict = None) -> Tuple[float, Dict]:
        """Calculate enhanced product score with multiple criteria. Max ~170 points."""

        score = 50  # Base score
        breakdown = {
            'base': 50, 'price': 0, 'images': 0,
            'demand': 0, 'quality': 0, 'penalty': 0
        }

        title = product.get('title', product.get('name', '')).lower()
        description = product.get('description', '').lower()
        text = f"{title} {description}"

        # 1. PRICE SCORE (0-25 points)
        original_price = price / 1.4
        if 15 <= price <= 60:
            breakdown['price'] = 25
        elif 10 <= price < 15 or 60 < price <= 80:
            breakdown['price'] = 18
        elif 5 <= price < 10 or 80 < price <= 100:
            breakdown['price'] = 10
        elif price > 100:
            breakdown['price'] = 5
        else:
            breakdown['price'] = 0

        profit_margin = ((price - original_price) / original_price) * 100
        if profit_margin >= 50:
            breakdown['price'] += 5
        elif profit_margin >= 40:
            breakdown['price'] += 3

        score += breakdown['price']

        # 2. IMAGE SCORE (0-30 points)
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

        for img in images:
            if 's-l1600' in img or 's-l1200' in img:
                breakdown['images'] += 2
                break

        score += breakdown['images']

        # 3. DEMAND SIGNALS (0-40 points)
        demand_score = 0
        for keyword in self.demand_keywords:
            if keyword in text:
                demand_score += 8
                if demand_score >= 40:
                    break

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

        # 4. QUALITY SIGNALS (0-25 points)
        quality_score = 0

        title_length = len(title)
        if 30 <= title_length <= 120:
            quality_score += 8
        elif 20 <= title_length < 30 or 120 < title_length <= 150:
            quality_score += 4

        desc_length = len(description)
        if desc_length > 200:
            quality_score += 7
        elif desc_length > 100:
            quality_score += 4
        elif desc_length > 50:
            quality_score += 2

        premium_brands = ['apple', 'samsung', 'sony', 'bose', 'anker', 'spigen', 'otterbox', 'belkin']
        for brand in premium_brands:
            if brand in text:
                quality_score += 5
                break

        if keywords_dict:
            positive = keywords_dict.get('positive', [])
            for keyword in positive[:5]:
                if keyword.lower() in title:
                    quality_score += 3
                    break

        breakdown['quality'] = min(quality_score, 25)
        score += breakdown['quality']

        # 5. PENALTIES (-10 to -50 points)
        penalty = 0
        for keyword in self.penalty_keywords:
            if keyword in text:
                penalty += 10
                if penalty >= 50:
                    break

        if len(title) < 15:
            penalty += 10
        if len(description) < 20:
            penalty += 8
        if image_count == 1:
            penalty += 5

        breakdown['penalty'] = -min(penalty, 50)
        score += breakdown['penalty']

        return max(score, 0), breakdown


# ===================================================================
# STANDALONE TEST - run: python services/product_scoring.py
# Delete this function when no longer needed
# ===================================================================

def _test():
    import sys, os, json
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    test_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'test', 'test_store_data.json')
    with open(test_file, encoding='utf-8') as f:
        test_data = json.load(f)

    class TestScoring(ProductScoringMixin):
        """Minimal test class with mocked cross-mixin dependencies"""
        def _extract_price(self, product):
            try:
                return float(product.get('price', 19.99))
            except:
                return 19.99

        def _extract_images(self, product):
            url = product.get('image_url', product.get('images', ''))
            return [url] if url else []

        def _parse_product(self, product):
            return {
                'title': product.get('title', ''),
                'price': str(self._extract_price(product)),
                'images': self._extract_images(product),
                'sku': f"TEST-{product.get('item_id', '0')}",
                'stock': 10,
                'description': ''
            }

    t = TestScoring()
    t._enhance_products_batch = lambda *_: None  # mock: no-op
    t.max_products = 3
    t.demand_keywords = ['premium', 'popular', 'best seller', 'top rated', 'professional']
    t.penalty_keywords = ['cheap', 'bulk', 'wholesale', 'used', 'refurbished']

    products = test_data['raw_products']

    print("=" * 60)
    print("TEST: product_scoring.py")
    print("=" * 60)
    print(f"Input: {len(products)} raw products\n")

    scored = t._score_all_products(products, "phone_cases")
    best = t._select_best_products(scored, t.max_products)

    print(f"\n[RESULT] Scored {len(products)} products → selected {len(best)} best")
    for i, p in enumerate(best, 1):
        title = p.get('title', 'N/A')
        score = p.get('final_score', p.get('relevance_score', 0))
        print(f"  {i}. Score {score:.0f} | {title[:55]}")

    print("\n[DONE] product_scoring.py test complete")


if __name__ == '__main__':
    _test()
