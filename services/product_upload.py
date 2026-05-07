"""
Product Upload Mixin - Shopify Upload & Hero Image
Handles uploading products to Shopify and setting the hero/banner image.
"""

import json
import logging
import os
import re
import time
import requests
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Hero section type identifiers — used by _find_hero_section()
_HERO_SECTION_TYPES = ('image-banner', 'image_banner', 'hero', 'slideshow', 'banner')

# Preferred image_picker setting IDs (in order) when multiple exist in a section schema
_IMAGE_PICKER_PREFERENCE = (
    "image", "image_1", "banner_image", "background_image",
    "hero_image", "media", "media_1"
)


# ---------------------------------------------------------------------------
# Module-level helpers for the theme-update portion of upload_hero_image()
# These are pure functions: no self, no class state.
# ---------------------------------------------------------------------------

def _fetch_template(shopify_url: str, headers: dict):
    """
    Return (theme_id, template_dict) for the active Shopify theme,
    or (None, None) on any failure.
    """
    resp = requests.get(f"{shopify_url}/themes.json", headers=headers, timeout=15)
    if not resp or resp.status_code != 200:
        logger.error("themes.json HTTP %s", getattr(resp, "status_code", "?"))
        return None, None

    themes = (resp.json() if resp.content else {}).get("themes") or []
    active = next((t for t in themes if (t or {}).get("role") == "main"), None)
    if not active:
        logger.error("No active (main) theme found")
        return None, None

    theme_id = active.get("id")
    if not theme_id:
        logger.error("Active theme has no id field")
        return None, None

    resp = requests.get(
        f"{shopify_url}/themes/{theme_id}/assets.json",
        headers=headers,
        params={"asset[key]": "templates/index.json"},
        timeout=15
    )
    if not resp or resp.status_code != 200:
        logger.error("Cannot read templates/index.json: HTTP %s",
                     getattr(resp, "status_code", "?"))
        return None, None

    raw = ((resp.json() if resp.content else {}).get("asset") or {}).get("value") or ""
    if not raw:
        logger.error("templates/index.json asset value is empty")
        return None, None

    try:
        template = json.loads(raw)
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        logger.error("templates/index.json JSON parse error: %s", exc)
        return None, None

    if not isinstance(template, dict):
        logger.error("templates/index.json is not a JSON object")
        return None, None

    return theme_id, template


def _find_hero_section(sections: dict):
    """
    Return the first section key whose type is in _HERO_SECTION_TYPES, or None.
    Checks all standard hero/banner section type names.
    """
    for key, section in sections.items():
        if isinstance(section, dict) and section.get("type") in _HERO_SECTION_TYPES:
            return key
    return None


def _update_hero_settings(sections: dict, hero_key: str,
                          file_ref: str, image_setting_id: str) -> None:
    """
    Write the image reference into the schema-validated image_picker setting.
    Only writes the one key confirmed to exist in the section's schema.
    Initialises settings dict if absent or None.
    """
    section = sections[hero_key]
    if not isinstance(section.get("settings"), dict):
        section["settings"] = {}
    section["settings"][image_setting_id] = file_ref


def _save_template(shopify_url: str, headers: dict, theme_id, template: dict) -> bool:
    """
    PUT templates/index.json back to Shopify.
    Returns True on HTTP 200/201, False otherwise.
    """
    resp = requests.put(
        f"{shopify_url}/themes/{theme_id}/assets.json",
        headers=headers,
        json={"asset": {"key": "templates/index.json",
                        "value": json.dumps(template, indent=2)}},
        timeout=30
    )
    if not resp or resp.status_code not in (200, 201):
        logger.error("Template write failed: HTTP %s",
                     getattr(resp, "status_code", "?"))
        return False
    return True


def _verify_template(shopify_url: str, headers: dict, theme_id,
                     hero_key: str, image_setting_id: str) -> None:
    """
    Read back templates/index.json and log whether the image setting was persisted.
    Never raises — wrapped in try/except so it never blocks the return value.
    """
    try:
        vr = requests.get(
            f"{shopify_url}/themes/{theme_id}/assets.json",
            headers=headers,
            params={"asset[key]": "templates/index.json"},
            timeout=15
        )
        if not vr or vr.status_code != 200:
            return
        raw = ((vr.json() if vr.content else {}).get("asset") or {}).get("value") or ""
        saved = json.loads(raw) if raw else {}
        settings = (
            ((saved.get("sections") or {}).get(hero_key) or {}).get("settings") or {}
        )
        if settings.get(image_setting_id):
            logger.info("Verified: %s saved as: %s",
                        image_setting_id, settings[image_setting_id])
        else:
            logger.warning("%s NOT found in saved template — Shopify may have rejected it",
                           image_setting_id)
    except Exception as ve:
        logger.warning("Verification read failed: %s", ve)


def _fetch_section_schema(shopify_url: str, headers: dict, theme_id, section_type: str):
    """
    Fetch sections/{section_type}.liquid and return its parsed {% schema %} dict,
    or None on any failure.
    """
    resp = requests.get(
        f"{shopify_url}/themes/{theme_id}/assets.json",
        headers=headers,
        params={"asset[key]": f"sections/{section_type}.liquid"},
        timeout=15
    )
    if not resp or resp.status_code != 200:
        logger.error("Cannot read sections/%s.liquid: HTTP %s",
                     section_type, getattr(resp, "status_code", "?"))
        return None

    liquid = ((resp.json() if resp.content else {}).get("asset") or {}).get("value") or ""
    if not liquid:
        logger.error("sections/%s.liquid is empty", section_type)
        return None

    match = re.search(
        r'\{%-?\s*schema\s*-?%\}(.*?)\{%-?\s*endschema\s*-?%\}',
        liquid, re.DOTALL | re.IGNORECASE
    )
    if not match:
        logger.error("No {%% schema %%} block found in sections/%s.liquid", section_type)
        return None

    try:
        schema = json.loads(match.group(1).strip())
    except (json.JSONDecodeError, ValueError) as exc:
        logger.error("Schema JSON parse error in sections/%s.liquid: %s", section_type, exc)
        return None

    if not isinstance(schema, dict):
        logger.error("Schema in sections/%s.liquid is not a JSON object", section_type)
        return None

    return schema


def _find_image_picker_id(schema: dict):
    """
    Return the setting id to use for the hero image, or None if no image_picker found.

    Rules:
    - Collect all settings with type == "image_picker"
    - If exactly one → return its id
    - If multiple → return the first id that matches _IMAGE_PICKER_PREFERENCE,
      then fall back to the first picker with any id
    """
    pickers = [
        s for s in (schema.get("settings") or [])
        if isinstance(s, dict) and s.get("type") == "image_picker" and s.get("id")
    ]
    if not pickers:
        return None
    if len(pickers) == 1:
        return pickers[0]["id"]

    picker_ids = {s["id"] for s in pickers}
    for preferred in _IMAGE_PICKER_PREFERENCE:
        if preferred in picker_ids:
            return preferred

    return pickers[0]["id"]


# ---------------------------------------------------------------------------


class ProductUploadMixin:
    """Mixin for Shopify upload operations"""

    def upload_to_shopify(self, product: Dict) -> bool:
        """
        Upload a single product to Shopify.

        Handles two input formats:
          Flat (from _parse_product):
            title, description, price, sku, stock, images=[url, ...]
          Shopify-ready (from processed_products JSON):
            title, body_html, vendor, variants=[{price, sku}], images=[{src}]
        """

        title       = (product.get("title") or "Untitled Product")[:255]
        description = product.get("description") or product.get("body_html") or ""

        price = product.get("price")
        if not price:
            variants = product.get("variants") or []
            price = variants[0].get("price", "19.99") if variants else "19.99"
        price = str(price)

        sku = product.get("sku")
        if not sku:
            variants = product.get("variants") or []
            sku = variants[0].get("sku", "") if variants else ""

        stock = int(product.get("stock") or 10)

        image_urls = []
        for img in (product.get("images") or []):
            if isinstance(img, dict):
                url = img.get("src") or img.get("url") or ""
            else:
                url = str(img)
            if url:
                image_urls.append(url)

        shopify_data: Dict = {
            "product": {
                "title": title,
                "body_html": description,
                "vendor": product.get("vendor") or "Premium Supplier",
                "product_type": "Electronics Accessories",
                "tags": "electronics, accessories, premium",
                "variants": [{
                    "price": price,
                    "sku": sku,
                    "inventory_management": "shopify",
                    "inventory_quantity": stock
                }]
            }
        }

        if image_urls:
            shopify_data["product"]["images"] = [{"src": u} for u in image_urls]

        try:
            resp = requests.post(
                f"{self.shopify_url}/products.json",
                headers=self.shopify_headers,
                json=shopify_data,
                timeout=30
            )
            if resp.status_code == 201:
                return True

            logger.error("Product upload failed: HTTP %s — %s",
                         resp.status_code, resp.text[:200])
            return False

        except Exception as exc:
            logger.error("Product upload exception: %s", exc)
            return False

    def upload_hero_image(self, image_path: Optional[str] = None) -> bool:
        """Upload image to Shopify Files via GraphQL and apply to homepage hero section."""

        shopify_url     = getattr(self, "shopify_url", None)
        shopify_headers = getattr(self, "shopify_headers", None)

        if not shopify_url or not shopify_url.startswith("https://"):
            logger.error("upload_hero_image: invalid or missing shopify_url")
            return False

        if not shopify_headers or not shopify_headers.get("X-Shopify-Access-Token"):
            logger.error("upload_hero_image: missing X-Shopify-Access-Token")
            return False

        if not image_path:
            photo_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "data", "photo"
            )
            if os.path.isdir(photo_dir):
                for fname in os.listdir(photo_dir):
                    if fname.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                        image_path = os.path.join(photo_dir, fname)
                        break

        if not image_path or not os.path.exists(image_path):
            logger.warning("upload_hero_image: no hero image found in data/photo/ — skipping")
            return False

        image_filename = os.path.basename(image_path)
        ext  = os.path.splitext(image_filename)[1].lower().lstrip(".")
        mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
                "png": "image/png",  "webp": "image/webp"}.get(ext, "image/png")
        gql_url = f"{shopify_url}/graphql.json"

        logger.info("STEP: Uploading hero image — %s", image_filename)

        try:
            with open(image_path, "rb") as fh:
                file_bytes = fh.read()

            # ── Step 1: stagedUploadsCreate ──────────────────────────────
            resp = requests.post(
                gql_url,
                headers=shopify_headers,
                json={
                    "query": """
                        mutation stagedUploadsCreate($input: [StagedUploadInput!]!) {
                            stagedUploadsCreate(input: $input) {
                                stagedTargets {
                                    url
                                    resourceUrl
                                    parameters { name value }
                                }
                                userErrors { field message }
                            }
                        }
                    """,
                    "variables": {
                        "input": [{
                            "resource": "FILE",
                            "filename": image_filename,
                            "mimeType": mime,
                            "httpMethod": "POST"
                        }]
                    }
                },
                timeout=30
            )

            if not resp or resp.status_code != 200:
                logger.error("stagedUploadsCreate HTTP %s",
                             getattr(resp, "status_code", "?"))
                return False

            body = resp.json() if resp.content else {}
            if "data" not in body:
                logger.error("stagedUploadsCreate: no 'data' in response")
                return False

            sue = (body["data"] or {}).get("stagedUploadsCreate") or {}
            if sue.get("userErrors"):
                logger.error("stagedUploadsCreate userErrors: %s", sue["userErrors"])
                return False

            targets = sue.get("stagedTargets") or []
            if not targets:
                logger.error("stagedUploadsCreate: no staged targets returned")
                return False

            target       = targets[0] or {}
            upload_url   = target.get("url")
            resource_url = target.get("resourceUrl")
            parameters   = target.get("parameters") or []

            if not upload_url or not resource_url:
                logger.error("stagedUploadsCreate: missing url or resourceUrl in target")
                return False

            # ── Step 2: Upload binary via multipart/form-data ────────────
            fields = [(p["name"], (None, p["value"])) for p in parameters if p.get("name")]
            fields.append(("file", (image_filename, file_bytes, mime)))

            up = requests.post(upload_url, files=fields, timeout=120)
            if not up or up.status_code not in (200, 201, 204):
                logger.error("Staged binary upload failed: HTTP %s",
                             getattr(up, "status_code", "?"))
                return False

            # ── Step 3: fileCreate ───────────────────────────────────────
            resp = requests.post(
                gql_url,
                headers=shopify_headers,
                json={
                    "query": """
                        mutation fileCreate($files: [FileCreateInput!]!) {
                            fileCreate(files: $files) {
                                files { id fileStatus }
                                userErrors { field message }
                            }
                        }
                    """,
                    "variables": {
                        "files": [{
                            "originalSource": resource_url,
                            "contentType": "IMAGE"
                        }]
                    }
                },
                timeout=30
            )

            if not resp or resp.status_code != 200:
                logger.error("fileCreate HTTP %s", getattr(resp, "status_code", "?"))
                return False

            body = resp.json() if resp.content else {}
            if "data" not in body:
                logger.error("fileCreate: no 'data' in response")
                return False

            fc = (body["data"] or {}).get("fileCreate") or {}
            if fc.get("userErrors"):
                logger.error("fileCreate userErrors: %s", fc["userErrors"])
                return False

            files_list = fc.get("files") or []
            if not files_list:
                logger.error("fileCreate: no files returned in response")
                return False

            file_id = (files_list[0] or {}).get("id") or ""
            if not file_id:
                logger.error("fileCreate: no file id returned")
                return False

            # ── Step 4: Poll until file status is READY ──────────────────
            _poll_query = """
                query getFile($id: ID!) {
                    node(id: $id) {
                        ... on MediaImage {
                            fileStatus
                            image { url }
                            preview { image { url } }
                        }
                    }
                }
            """

            cdn_url   = ""
            max_polls = 10

            for attempt in range(1, max_polls + 1):
                time.sleep(1)
                pr = requests.post(
                    gql_url,
                    headers=shopify_headers,
                    json={"query": _poll_query, "variables": {"id": file_id}},
                    timeout=15
                )
                if not pr or pr.status_code != 200:
                    logger.warning("File poll attempt %d: HTTP %s",
                                   attempt, getattr(pr, "status_code", "?"))
                    continue

                node   = ((pr.json() if pr.content else {}).get("data") or {}).get("node") or {}
                status = node.get("fileStatus") or ""

                logger.info("File status: %s (attempt %d/%d)", status or "UNKNOWN", attempt, max_polls)

                if status == "READY":
                    cdn_url = (
                        (node.get("image") or {}).get("url")
                        or ((node.get("preview") or {}).get("image") or {}).get("url")
                        or ""
                    )
                    if cdn_url:
                        break
                    logger.warning("File READY but cdn_url still empty on attempt %d", attempt)

            if not cdn_url:
                logger.error("fileCreate: file not ready after %d attempts — id: %s",
                             max_polls, file_id)
                return False

            # Build Shopify file reference
            filename = cdn_url.split("/")[-1].split("?")[0]
            file_ref = f"shopify://shop_images/{filename}"
            logger.info("Hero file ready: %s", file_ref)

            # ── Steps 5–6: Fetch active theme + templates/index.json ─────
            theme_id, template = _fetch_template(shopify_url, shopify_headers)
            if theme_id is None or template is None:
                return False

            # ── Step 7: Detect hero section ──────────────────────────────
            sections = template.get("sections") or {}
            hero_key = _find_hero_section(sections)
            if not hero_key:
                logger.error(
                    "No hero section found — section types present: %s",
                    [s.get("type") for s in sections.values() if isinstance(s, dict)]
                )
                return False

            section_type = sections[hero_key].get("type") or ""
            logger.info("Hero section: key=%s  type=%s", hero_key, section_type)

            # ── Step 7.5: Resolve image_picker setting from section schema ──
            schema = _fetch_section_schema(shopify_url, shopify_headers, theme_id, section_type)
            if schema is None:
                logger.error("Cannot read schema for section type '%s'", section_type)
                return False

            image_setting_id = _find_image_picker_id(schema)
            if not image_setting_id:
                logger.error(
                    "No image_picker setting found in schema for section type '%s'",
                    section_type
                )
                return False

            logger.info("Image picker setting ID resolved: %s", image_setting_id)

            # ── Step 8: Write validated image setting ────────────────────
            _update_hero_settings(sections, hero_key, file_ref, image_setting_id)
            template["sections"] = sections
            logger.info("%s = %s", image_setting_id, file_ref)

            # ── Step 9: Persist template ─────────────────────────────────
            if not _save_template(shopify_url, shopify_headers, theme_id, template):
                return False

            logger.info("Template pushed — hero image live on storefront")

            # ── Step 10: Verify persistence ──────────────────────────────
            _verify_template(shopify_url, shopify_headers, theme_id, hero_key, image_setting_id)

            return True

        except Exception as exc:
            logger.error("upload_hero_image failed: %s", exc)
            return False


# ===================================================================
# STANDALONE TEST — run: python services/product_upload.py
# Makes REAL API calls to the test store in test_store_data.json
# Delete this function when no longer needed
# ===================================================================

def _test():
    import sys, os, json
    import logging as _logging
    _logging.basicConfig(level=_logging.DEBUG,
                         format="%(levelname)s %(name)s — %(message)s")

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, root)

    test_file = os.path.join(root, "data", "test", "test_store_data.json")
    with open(test_file, encoding="utf-8") as f:
        test_data = json.load(f)

    store_info = test_data["store_info"]
    store_host = (
        store_info["store_url"]
        .replace("https://", "")
        .replace("http://", "")
        .split("/")[0]
    )

    class TestUpload(ProductUploadMixin):
        pass

    t = TestUpload()
    t.shopify_store   = store_host
    t.shopify_url     = f"https://{store_host}/admin/api/2024-01"
    t.shopify_headers = {
        "X-Shopify-Access-Token": store_info["access_token"],
        "Content-Type": "application/json"
    }

    product  = test_data["processed_products"][0]
    variants = product.get("variants") or [{}]

    print("=" * 60)
    print("TEST: upload_to_shopify  (REAL API CALL)")
    print("=" * 60)
    print(f"Store  : {t.shopify_store}")
    print(f"Title  : {product.get('title', 'N/A')}")
    print(f"Price  : ${variants[0].get('price', 'N/A')}")
    print(f"SKU    : {variants[0].get('sku', 'N/A')}")
    print(f"Images : {len(product.get('images', []))}")
    print()

    result = t.upload_to_shopify(product)
    print(f"[RESULT] Product upload: {'SUCCESS' if result else 'FAILED'}")

    print("\n" + "=" * 60)
    print("TEST: upload_hero_image  (REAL API CALL)")
    print("=" * 60)

    hero_result = t.upload_hero_image()
    print(f"[RESULT] Hero image: {'SUCCESS' if hero_result else 'FAILED'}")

    print("\n[DONE] product_upload.py test complete")


if __name__ == "__main__":
    
    _test()
