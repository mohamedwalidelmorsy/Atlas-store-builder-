#!/usr/bin/env python3
"""
debug_shopify_store_password.py

DEBUG + DIAGNOSTIC TOOL
-----------------------
Opens a Shopify Admin store, navigates to Online Store  Preferences  Password protection,
and attempts to extract the store password using multiple fallback strategies.

Run independently. Never modifies the main automation flow.
"""

import os
import re
import sys
import json
import time
import traceback
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
    StaleElementReferenceException,
)

# ========================================================
# CONFIGURATION
# ========================================================

load_dotenv()

ADMIN_URL = os.getenv(
    "SHOPIFY_ADMIN_PREFERENCES_URL",
    "https://admin.shopify.com/store/efgrdsd-20260216-153700/online_store/preferences",
)
SHOPIFY_DEV_EMAIL = os.getenv("SHOPIFY_DEV_EMAIL", "")
SHOPIFY_DEV_PASSWORD = os.getenv("SHOPIFY_DEV_PASSWORD", "")

SCREENSHOT_DIR = Path("debug_screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)

REPORT: list[dict] = []


# ========================================================
# UTILITIES
# ========================================================


def log(msg: str) -> None:
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] {msg}")


def save_screenshot(driver: webdriver.Chrome, label: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = SCREENSHOT_DIR / f"{label}_{ts}.png"
    try:
        driver.save_screenshot(str(filename))
        log(f"   Screenshot saved: {filename}")
    except Exception as exc:
        log(f"    Screenshot failed: {exc}")
    return str(filename)


def record(strategy: str, success: bool, value: str | None, reason: str) -> None:
    entry = {
        "strategy": strategy,
        "success": success,
        "value": value,
        "reason": reason,
    }
    REPORT.append(entry)
    status = " SUCCESS" if success else " FAIL"
    log(f"  {status} | {strategy} | {reason}")


def human_delay(lo: float = 0.5, hi: float = 1.5) -> None:
    import random
    time.sleep(random.uniform(lo, hi))


# ========================================================
# BROWSER SETUP
# ========================================================


def create_driver() -> webdriver.Chrome:
    log("Setting up Chrome browser (headed, stealth options)...")
    opts = Options()

    # Stealth / anti-detection
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--disable-infobars")
    opts.add_argument("--start-maximized")
    opts.add_argument("--no-first-run")
    opts.add_argument("--no-default-browser-check")
    opts.add_argument("--disable-popup-blocking")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)

    # Headed mode  do NOT add --headless
    driver = webdriver.Chrome(options=opts)

    # Remove webdriver flag
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                window.chrome = {runtime: {}};
            """
        },
    )

    driver.implicitly_wait(5)
    log("Browser ready.")
    return driver


# ========================================================
# LOGIN FLOW
# ========================================================


def login_shopify_partners(driver: webdriver.Chrome) -> bool:
    """Login to Shopify Partners / Admin via accounts.shopify.com."""
    log("Navigating to Shopify login...")
    try:
        driver.get("https://accounts.shopify.com/lookup")
        human_delay(1, 2)

        # --- Email step ---
        try:
            email_input = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "input[name='account[email]'], input[type='email'], #account_email")
                )
            )
            email_input.clear()
            for ch in SHOPIFY_DEV_EMAIL:
                email_input.send_keys(ch)
                time.sleep(0.04)
            log(f"  Entered email: {SHOPIFY_DEV_EMAIL}")
            human_delay(0.5, 1)

            # Click continue / next
            btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            btn.click()
            human_delay(2, 3)
        except Exception as exc:
            log(f"    Email step issue: {exc}")
            save_screenshot(driver, "login_email_error")

        # --- Password step ---
        try:
            pw_input = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "input[name='account[password]'], input[type='password']")
                )
            )
            pw_input.clear()
            for ch in SHOPIFY_DEV_PASSWORD:
                pw_input.send_keys(ch)
                time.sleep(0.04)
            log("  Entered password.")
            human_delay(0.5, 1)

            btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            btn.click()
            human_delay(3, 5)
        except Exception as exc:
            log(f"    Password step issue: {exc}")
            save_screenshot(driver, "login_password_error")

        # Verify we reached a Shopify domain
        current = driver.current_url
        if "shopify.com" in current and "lookup" not in current:
            log(f"  Login appears successful. URL: {current}")
            return True
        else:
            log(f"  Login may have failed. URL: {current}")
            save_screenshot(driver, "login_uncertain")
            return False

    except Exception as exc:
        log(f"  Login error: {exc}")
        save_screenshot(driver, "login_exception")
        return False


# ========================================================
# NAVIGATE TO PREFERENCES
# ========================================================


def handle_store_selector(driver: webdriver.Chrome) -> bool:
    """Handle the accounts.shopify.com/select store picker page."""
    log("  Store selector page detected. Picking the correct store...")
    try:
        human_delay(2, 3)
        save_screenshot(driver, "store_selector_page")

        # Extract store name from ADMIN_URL (e.g. "efgrdsd-20260216-153700")
        store_slug = ADMIN_URL.split("/store/")[1].split("/")[0] if "/store/" in ADMIN_URL else ""
        log(f"  Looking for store slug: '{store_slug}'")

        # Strategy 1: Click a link/card that contains the store slug text
        if store_slug:
            store_link_xpaths = [
                f"//a[contains(@href, '{store_slug}')]",
                f"//*[contains(text(), '{store_slug}')]//ancestor::a",
                f"//*[contains(text(), '{store_slug}')]",
            ]
            for xpath in store_link_xpaths:
                try:
                    elements = driver.find_elements(By.XPATH, xpath)
                    for el in elements:
                        if el.is_displayed():
                            log(f"  Found store element: {el.tag_name} - clicking...")
                            try:
                                el.click()
                            except Exception:
                                driver.execute_script("arguments[0].click();", el)
                            human_delay(3, 5)
                            log(f"  After click URL: {driver.current_url}")
                            return True
                except Exception:
                    continue

        # Strategy 2: Click the first store card/link on the page
        log("  Trying to click first available store...")
        card_selectors = [
            "a[href*='admin.shopify.com/store']",
            "[class*='StoreCard'] a",
            "[class*='store'] a",
            "a[href*='myshopify.com']",
        ]
        for css in card_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, css)
                for el in elements:
                    if el.is_displayed():
                        log(f"  Found store link: {el.get_attribute('href') or 'N/A'}")
                        try:
                            el.click()
                        except Exception:
                            driver.execute_script("arguments[0].click();", el)
                        human_delay(3, 5)
                        return True
            except Exception:
                continue

        # Strategy 3: Just navigate directly to the admin URL again
        log("  Could not find store card. Navigating directly to admin URL...")
        driver.get(ADMIN_URL)
        human_delay(5, 8)
        return True

    except Exception as exc:
        log(f"  Store selector handling error: {exc}")
        save_screenshot(driver, "store_selector_error")
        return False


def navigate_to_preferences(driver: webdriver.Chrome) -> bool:
    log(f"Navigating directly to: {ADMIN_URL}")
    try:
        driver.get(ADMIN_URL)
        human_delay(3, 5)

        # Wait for page to be somewhat loaded
        WebDriverWait(driver, 20).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        human_delay(1, 2)

        current = driver.current_url
        title = driver.title
        log(f"  Page loaded. URL: {current}")
        log(f"  Title: {title}")

        # Handle store selector page (accounts.shopify.com/select)
        if "accounts.shopify.com/select" in current or "accounts.shopify.com/lookup" in current:
            log("  Redirected to store selector / login page.")
            if not handle_store_selector(driver):
                log("  Failed to handle store selector.")
                save_screenshot(driver, "store_selector_failed")
                return False

            # After store selection, navigate to preferences again
            human_delay(2, 3)
            current = driver.current_url
            log(f"  After store selection URL: {current}")

            # If we're in admin but not on preferences, navigate there
            if "admin.shopify.com" in current and "/preferences" not in current:
                log("  In admin but not on preferences. Navigating...")
                driver.get(ADMIN_URL)
                human_delay(3, 5)
                WebDriverWait(driver, 20).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                human_delay(1, 2)
                current = driver.current_url
                log(f"  Final URL: {current}")

        # Verify we're on the right page
        current = driver.current_url
        if "preferences" in current:
            log("  On Preferences page.")
            return True

        # Check for password-related content on the page
        body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        if "password" in body_text or "preferences" in body_text or "online store" in body_text:
            log("  Page contains expected content.")
            return True
        else:
            log("  Page may not have loaded correctly (no expected text found).")
            save_screenshot(driver, "preferences_page_check")
            return True  # proceed anyway

    except Exception as exc:
        log(f"  Navigation error: {exc}")
        save_screenshot(driver, "navigation_error")
        return False


# ========================================================
# STRATEGY 1: STRICT DOM SELECTOR
# ========================================================


def strategy_strict_dom(driver: webdriver.Chrome) -> None:
    name = "STRATEGY 1: STRICT DOM SELECTOR"
    log(f"Running {name}...")
    try:
        xpath = (
            "//input[@type='text' and @maxlength='100' "
            "and contains(@class,'Polaris-TextField__Input')]"
        )
        elements = driver.find_elements(By.XPATH, xpath)
        if not elements:
            record(name, False, None, "No elements matched the strict XPath selector.")
            return

        for i, el in enumerate(elements):
            val = el.get_attribute("value") or ""
            log(f"  Found element [{i}]: value='{val}', displayed={el.is_displayed()}")
            if val.strip():
                record(name, True, val.strip(), f"Extracted from element index {i}.")
                return

        record(name, False, None, f"Found {len(elements)} element(s) but all had empty value.")

    except Exception as exc:
        record(name, False, None, f"Exception: {exc}")
        save_screenshot(driver, "strategy1_error")


# ========================================================
# STRATEGY 2: LABEL-BASED MATCHING
# ========================================================


def strategy_label_based(driver: webdriver.Chrome) -> None:
    name = "STRATEGY 2: LABEL-BASED MATCHING"
    log(f"Running {name}...")
    try:
        # Try multiple ways to find a label containing "Password"
        labels = driver.find_elements(
            By.XPATH,
            "//label[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
            "'abcdefghijklmnopqrstuvwxyz'),'password')]",
        )
        if not labels:
            # Also try span-based Polaris labels
            labels = driver.find_elements(
                By.XPATH,
                "//span[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                "'abcdefghijklmnopqrstuvwxyz'),'password')]/ancestor::label",
            )

        if not labels:
            record(name, False, None, "No label with 'Password' text found.")
            return

        for label in labels:
            log(f"  Found label: text='{label.text.strip()}', for='{label.get_attribute('for')}'")

            # Method A: 'for' attribute
            for_attr = label.get_attribute("for")
            if for_attr:
                try:
                    inp = driver.find_element(By.ID, for_attr)
                    val = inp.get_attribute("value") or ""
                    if val.strip():
                        record(name, True, val.strip(), f"Matched via label 'for' attr  id='{for_attr}'.")
                        return
                except NoSuchElementException:
                    pass

            # Method B: closest sibling/descendant input
            try:
                parent = label.find_element(By.XPATH, "..")
                inputs = parent.find_elements(By.TAG_NAME, "input")
                for inp in inputs:
                    val = inp.get_attribute("value") or ""
                    if val.strip():
                        record(name, True, val.strip(), "Matched via sibling input of label parent.")
                        return
            except Exception:
                pass

            # Method C: aria-labelledby
            label_id = label.get_attribute("id")
            if label_id:
                try:
                    inp = driver.find_element(
                        By.XPATH, f"//input[@aria-labelledby='{label_id}']"
                    )
                    val = inp.get_attribute("value") or ""
                    if val.strip():
                        record(name, True, val.strip(), f"Matched via aria-labelledby='{label_id}'.")
                        return
                except NoSuchElementException:
                    pass

        record(name, False, None, "Labels found but no associated input had a value.")

    except Exception as exc:
        record(name, False, None, f"Exception: {exc}")
        save_screenshot(driver, "strategy2_error")


# ========================================================
# STRATEGY 3: ARIA-BASED DETECTION
# ========================================================


def strategy_aria_based(driver: webdriver.Chrome) -> None:
    name = "STRATEGY 3: ARIA-BASED DETECTION"
    log(f"Running {name}...")
    try:
        # aria-labelledby containing "Password"
        candidates = driver.find_elements(
            By.XPATH,
            "//input[contains(@aria-labelledby,'assword') or contains(@aria-labelledby,'password')]",
        )
        # aria-describedby containing "characters"
        candidates += driver.find_elements(
            By.XPATH,
            "//input[contains(@aria-describedby,'characters') or contains(@aria-describedby,'char')]",
        )

        if not candidates:
            record(name, False, None, "No inputs with matching aria attributes found.")
            return

        seen_ids = set()
        for el in candidates:
            el_id = el.get_attribute("id") or id(el)
            if el_id in seen_ids:
                continue
            seen_ids.add(el_id)

            val = el.get_attribute("value") or ""
            aria_lb = el.get_attribute("aria-labelledby") or ""
            aria_db = el.get_attribute("aria-describedby") or ""
            log(f"  Candidate: value='{val}', aria-labelledby='{aria_lb}', aria-describedby='{aria_db}'")

            if val.strip():
                record(name, True, val.strip(), f"Matched via aria attributes (labelledby='{aria_lb}').")
                return

        record(name, False, None, f"Found {len(seen_ids)} candidate(s) but none had a value.")

    except Exception as exc:
        record(name, False, None, f"Exception: {exc}")
        save_screenshot(driver, "strategy3_error")


# ========================================================
# STRATEGY 4: VISIBLE TEXTFIELD SCAN
# ========================================================


def strategy_visible_textfield(driver: webdriver.Chrome) -> None:
    name = "STRATEGY 4: VISIBLE TEXTFIELD SCAN"
    log(f"Running {name}...")
    try:
        inputs = driver.find_elements(
            By.CSS_SELECTOR, "input.Polaris-TextField__Input"
        )
        if not inputs:
            # Fallback: any text input
            inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='text']")

        log(f"  Found {len(inputs)} input(s) to scan.")
        for i, inp in enumerate(inputs):
            try:
                displayed = inp.is_displayed()
                enabled = inp.is_enabled()
                maxlen = inp.get_attribute("maxlength") or ""
                val = inp.get_attribute("value") or ""
                inp_type = inp.get_attribute("type") or ""
                inp_name = inp.get_attribute("name") or ""
                inp_id = inp.get_attribute("id") or ""

                log(
                    f"  [{i}] displayed={displayed}, enabled={enabled}, "
                    f"maxlength={maxlen}, type={inp_type}, name={inp_name}, "
                    f"id={inp_id}, value='{val[:30]}{'...' if len(val) > 30 else ''}'"
                )

                if displayed and enabled and maxlen == "100" and len(val.strip()) > 0:
                    record(name, True, val.strip(), f"Matched input index {i} (id='{inp_id}').")
                    return
            except StaleElementReferenceException:
                log(f"  [{i}] Stale element, skipping.")

        record(name, False, None, "No visible, enabled input with maxlength=100 and a value found.")

    except Exception as exc:
        record(name, False, None, f"Exception: {exc}")
        save_screenshot(driver, "strategy4_error")


# ========================================================
# STRATEGY 5: REACT VALUE ACCESS (JS)
# ========================================================


def strategy_react_value(driver: webdriver.Chrome) -> None:
    name = "STRATEGY 5: REACT VALUE ACCESS (JS)"
    log(f"Running {name}...")
    try:
        js = """
        var results = [];
        var inputs = document.querySelectorAll(
            'input.Polaris-TextField__Input, input[type="text"][maxlength="100"]'
        );
        inputs.forEach(function(el, idx) {
            var val1 = el.value || '';
            var val2 = '';
            var val3 = '';
            try {
                var descriptor = Object.getOwnPropertyDescriptor(
                    HTMLInputElement.prototype, 'value'
                );
                if (descriptor && descriptor.get) {
                    val2 = descriptor.get.call(el) || '';
                }
            } catch(e) { val2 = 'ERROR: ' + e.message; }

            // React internal fiber
            try {
                var keys = Object.keys(el);
                for (var i = 0; i < keys.length; i++) {
                    if (keys[i].startsWith('__reactFiber') || keys[i].startsWith('__reactInternalInstance')) {
                        var fiber = el[keys[i]];
                        if (fiber && fiber.memoizedProps && fiber.memoizedProps.value) {
                            val3 = fiber.memoizedProps.value;
                        }
                    }
                }
            } catch(e) { val3 = 'ERROR: ' + e.message; }

            results.push({
                index: idx,
                id: el.id || '',
                elValue: val1,
                descriptorValue: val2,
                reactValue: val3,
                maxlength: el.maxLength,
                displayed: el.offsetParent !== null
            });
        });
        return JSON.stringify(results);
        """
        raw = driver.execute_script(js)
        results = json.loads(raw) if raw else []

        if not results:
            record(name, False, None, "No candidate inputs found via JS.")
            return

        for r in results:
            log(f"  JS [{r['index']}]: id={r['id']}, el.value='{r['elValue']}', "
                f"descriptor='{r['descriptorValue']}', react='{r['reactValue']}', "
                f"displayed={r['displayed']}")

            # Pick the best non-empty value
            for key in ("elValue", "descriptorValue", "reactValue"):
                v = r.get(key, "")
                if v and not v.startswith("ERROR") and 1 <= len(v) <= 100:
                    record(name, True, v, f"Extracted via JS ({key}) from input index {r['index']}.")
                    return

        record(name, False, None, "JS found inputs but no non-empty values.")

    except Exception as exc:
        record(name, False, None, f"Exception: {exc}")
        save_screenshot(driver, "strategy5_error")


# ========================================================
# STRATEGY 6: DOM SNAPSHOT SCAN
# ========================================================


def strategy_dom_snapshot(driver: webdriver.Chrome) -> None:
    name = "STRATEGY 6: DOM SNAPSHOT SCAN"
    log(f"Running {name}...")
    try:
        html = driver.execute_script("return document.body.innerHTML;")
        if not html:
            record(name, False, None, "document.body.innerHTML was empty.")
            return

        log(f"  DOM snapshot length: {len(html)} chars.")

        # Look for value="..." patterns
        pattern = r'value="([^"]{1,100})"'
        matches = re.findall(pattern, html)

        # Filter out common non-password values
        ignore = {
            "", "true", "false", "on", "off", "submit", "button", "text",
            "hidden", "0", "1", "Save", "Cancel",
        }
        candidates = [
            m for m in matches
            if m.strip() and m.strip() not in ignore and not m.startswith("http")
        ]

        log(f"  Found {len(matches)} raw value attributes, {len(candidates)} candidates after filtering.")

        if not candidates:
            record(name, False, None, "No reasonable value= candidates found in DOM snapshot.")
            return

        for c in candidates[:10]:
            log(f"  Candidate value: '{c}'")

        # Heuristic: look near password-related context
        password_region = ""
        pw_idx = html.lower().find("password")
        if pw_idx != -1:
            start = max(0, pw_idx - 2000)
            end = min(len(html), pw_idx + 3000)
            password_region = html[start:end]
            region_matches = re.findall(pattern, password_region)
            region_candidates = [
                m for m in region_matches
                if m.strip() and m.strip() not in ignore and not m.startswith("http")
            ]
            if region_candidates:
                log(f"  Candidates near 'password' context: {region_candidates[:5]}")
                record(name, True, region_candidates[0],
                       f"Extracted from DOM near 'password' context. "
                       f"All near-context candidates: {region_candidates[:5]}")
                return

        # Fallback: return first candidate with a note
        record(name, True, candidates[0],
               f"No password-context match; returning first plausible candidate. "
               f"Total candidates: {candidates[:5]}")

    except Exception as exc:
        record(name, False, None, f"Exception: {exc}")
        save_screenshot(driver, "strategy6_error")


# ========================================================
# STRATEGY 7: LAST-RESORT VISUAL CONFIRMATION
# ========================================================


def strategy_visual_confirmation(driver: webdriver.Chrome) -> None:
    name = "STRATEGY 7: VISUAL CONFIRMATION"
    log(f"Running {name}...")
    try:
        # Scroll page slowly for visual inspection
        total_height = driver.execute_script("return document.body.scrollHeight")
        viewport = driver.execute_script("return window.innerHeight")
        scroll_pos = 0

        while scroll_pos < total_height:
            driver.execute_script(f"window.scrollTo(0, {scroll_pos});")
            time.sleep(0.3)
            scroll_pos += viewport // 2

        # Scroll back to top
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(0.5)

        # Highlight all candidate inputs
        js_highlight = """
        var inputs = document.querySelectorAll(
            'input.Polaris-TextField__Input, input[type="text"][maxlength="100"], input[type="text"]'
        );
        var info = [];
        inputs.forEach(function(el, idx) {
            el.style.outline = '3px solid red';
            el.style.background = 'rgba(255,0,0,0.1)';
            info.push({
                index: idx,
                id: el.id || '',
                name: el.name || '',
                type: el.type || '',
                value: el.value || '',
                maxlength: el.maxLength,
                placeholder: el.placeholder || '',
                className: el.className || '',
                rect: el.getBoundingClientRect().toJSON()
            });
        });
        return JSON.stringify(info);
        """
        raw = driver.execute_script(js_highlight)
        info_list = json.loads(raw) if raw else []

        log(f"  Highlighted {len(info_list)} input(s).")
        save_screenshot(driver, "strategy7_highlighted")

        for item in info_list:
            log(
                f"  Input [{item['index']}]: id='{item['id']}', name='{item['name']}', "
                f"value='{item['value']}', maxlength={item['maxlength']}, "
                f"placeholder='{item['placeholder']}', "
                f"rect=({item['rect'].get('x',0):.0f},{item['rect'].get('y',0):.0f},"
                f"{item['rect'].get('width',0):.0f}x{item['rect'].get('height',0):.0f})"
            )

            # Screenshot individual element if possible
            try:
                el = driver.find_elements(By.CSS_SELECTOR, "input")[item["index"]]
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                time.sleep(0.3)
                save_screenshot(driver, f"strategy7_input_{item['index']}")
            except Exception:
                pass

        if info_list:
            valued = [i for i in info_list if i["value"].strip()]
            if valued:
                record(name, True, valued[0]["value"],
                       f"Visual scan found {len(valued)} input(s) with values. "
                       f"Best candidate at index {valued[0]['index']}.")
            else:
                record(name, False, None,
                       f"Visual scan found {len(info_list)} inputs but none had values. "
                       "Screenshots saved for manual review.")
        else:
            record(name, False, None, "No inputs found on page for visual confirmation.")

    except Exception as exc:
        record(name, False, None, f"Exception: {exc}")
        save_screenshot(driver, "strategy7_error")


# ========================================================
# MAIN EXECUTION
# ========================================================


def switch_to_content_frame(driver: webdriver.Chrome) -> bool:
    """
    Detect if the Preferences page content is inside an iframe.
    If so, switch into it. Shopify admin sometimes renders page content
    inside iframes which makes standard selectors fail.
    Returns True if we switched into a frame (or found inputs in main doc).
    """
    log("Checking for iframes / embedded frames...")

    # First check: are there any inputs in the main document?
    main_input_count = driver.execute_script(
        "return document.querySelectorAll('input').length;"
    )
    log(f"  Inputs in main document: {main_input_count}")

    if main_input_count > 0:
        log("  Inputs found in main document - no frame switch needed.")
        return True

    # Get all iframes on the page
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    log(f"  Found {len(iframes)} iframe(s) on the page.")

    for i, frame in enumerate(iframes):
        frame_src = frame.get_attribute("src") or ""
        frame_name = frame.get_attribute("name") or ""
        frame_id = frame.get_attribute("id") or ""
        log(f"  iframe[{i}]: id='{frame_id}', name='{frame_name}', src='{frame_src[:100]}'")

        try:
            driver.switch_to.frame(frame)
            inner_inputs = driver.execute_script(
                "return document.querySelectorAll('input').length;"
            )
            log(f"    -> Inputs inside this iframe: {inner_inputs}")

            if inner_inputs > 0:
                # Check for password-related content
                body_text = driver.execute_script(
                    "return document.body ? document.body.innerText : '';"
                ) or ""
                has_password = "password" in body_text.lower() or "characters used" in body_text.lower()
                log(f"    -> Has password-related text: {has_password}")

                if has_password or inner_inputs >= 1:
                    log(f"  ** Switched into iframe[{i}] - found {inner_inputs} input(s) **")
                    return True

            # Not this frame, switch back
            driver.switch_to.default_content()
        except Exception as exc:
            log(f"    -> Error switching to iframe[{i}]: {exc}")
            try:
                driver.switch_to.default_content()
            except Exception:
                pass

    # Try shadow DOM traversal as last resort
    log("  Checking for Shadow DOM roots...")
    shadow_inputs = driver.execute_script("""
        function findInputsInShadow(root) {
            var inputs = [];
            var allElements = root.querySelectorAll('*');
            for (var i = 0; i < allElements.length; i++) {
                if (allElements[i].shadowRoot) {
                    var shadowInputs = allElements[i].shadowRoot.querySelectorAll('input');
                    for (var j = 0; j < shadowInputs.length; j++) {
                        inputs.push({
                            host: allElements[i].tagName,
                            value: shadowInputs[j].value || '',
                            type: shadowInputs[j].type || '',
                            maxlength: shadowInputs[j].maxLength
                        });
                    }
                    // Recurse into shadow roots
                    var deeper = findInputsInShadow(allElements[i].shadowRoot);
                    inputs = inputs.concat(deeper);
                }
            }
            return inputs;
        }
        return JSON.stringify(findInputsInShadow(document));
    """)
    shadow_results = json.loads(shadow_inputs) if shadow_inputs else []
    log(f"  Shadow DOM inputs found: {len(shadow_results)}")
    for sr in shadow_results:
        log(f"    host={sr['host']}, value='{sr['value']}', type={sr['type']}, maxlength={sr['maxlength']}")

    if not iframes and not shadow_results:
        log("  No iframes or shadow DOM found. Content might be loading dynamically.")
        # Try waiting a bit more and scrolling
        human_delay(3, 5)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
        human_delay(2, 3)
        driver.execute_script("window.scrollTo(0, 0);")
        human_delay(2, 3)

        # Check again
        after_scroll = driver.execute_script(
            "return document.querySelectorAll('input').length;"
        )
        log(f"  After scroll+wait: {after_scroll} inputs in main document.")
        return after_scroll > 0

    return len(shadow_results) > 0


def wait_for_page_ready(driver: webdriver.Chrome) -> bool:
    """Wait for Polaris React components to finish rendering on the Preferences page."""
    log("Waiting for Preferences page to fully render (React/Polaris)...")

    # First wait for the page itself to load
    human_delay(3, 5)
    save_screenshot(driver, "before_frame_check")

    # Check and switch into iframe if needed
    found = switch_to_content_frame(driver)
    if found:
        log("  Content frame found/switched. Checking for inputs...")
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR,
                    "input.Polaris-TextField__Input, input[type='text'][maxlength='100'], input[type='text']"
                ))
            )
            log("  Page rendered - input elements found.")
            human_delay(1, 2)
            return True
        except TimeoutException:
            log("  Frame switched but inputs still not found via WebDriverWait.")
            save_screenshot(driver, "frame_switched_no_inputs")
            return False
    else:
        log("  WARNING - No content frame with inputs found.")
        save_screenshot(driver, "no_content_frame")
        return False


def run_all_strategies(driver: webdriver.Chrome) -> None:
    # Wait for React/Polaris to finish rendering before running strategies
    wait_for_page_ready(driver)

    strategies = [
        strategy_strict_dom,
        strategy_label_based,
        strategy_aria_based,
        strategy_visible_textfield,
        strategy_react_value,
        strategy_dom_snapshot,
        strategy_visual_confirmation,
    ]
    for fn in strategies:
        log(f"\n{'='*60}")
        try:
            fn(driver)
        except Exception as exc:
            record(fn.__name__, False, None, f"Unhandled exception: {exc}")
            save_screenshot(driver, f"{fn.__name__}_unhandled")
        log("")


def print_final_report() -> None:
    log("\n" + "=" * 70)
    log("FINAL DIAGNOSTIC REPORT")
    log("=" * 70)

    successes = [r for r in REPORT if r["success"]]
    failures = [r for r in REPORT if not r["success"]]

    for entry in REPORT:
        status = "" if entry["success"] else ""
        val_display = f"  '{entry['value']}'" if entry["value"] else ""
        log(f"  {status} {entry['strategy']}{val_display}")
        log(f"     Reason: {entry['reason']}")

    log("-" * 70)
    if successes:
        best = successes[0]
        log(f" EXTRACTED PASSWORD: '{best['value']}'")
        log(f"   First successful strategy: {best['strategy']}")
        if len(successes) > 1:
            log(f"   ({len(successes)} strategies succeeded in total)")
    else:
        log(" NO PASSWORD COULD BE EXTRACTED.")
        log(f"   All {len(failures)} strategies failed.")

    log("=" * 70)

    # Save JSON report
    report_path = SCREENSHOT_DIR / "diagnostic_report.json"
    try:
        with open(report_path, "w") as f:
            json.dump(REPORT, f, indent=2)
        log(f" JSON report saved: {report_path}")
    except Exception as exc:
        log(f"  Failed to save JSON report: {exc}")


def main() -> None:
    log("=" * 70)
    log("SHOPIFY STORE PASSWORD DEBUG TOOL")
    log("=" * 70)

    if not SHOPIFY_DEV_EMAIL or not SHOPIFY_DEV_PASSWORD:
        log(" SHOPIFY_DEV_EMAIL or SHOPIFY_DEV_PASSWORD not set in .env")
        log("   Create a .env file with these variables or set them as environment variables.")
        sys.exit(1)

    log(f"  Target URL: {ADMIN_URL}")
    log(f"  Email: {SHOPIFY_DEV_EMAIL}")
    log(f"  Screenshots: {SCREENSHOT_DIR.resolve()}")

    driver = None
    try:
        driver = create_driver()

        # Step 1: Login
        logged_in = login_shopify_partners(driver)
        if not logged_in:
            log("  Login may have failed, but continuing anyway...")
            save_screenshot(driver, "post_login_status")

        # Step 2: Navigate to preferences
        human_delay(1, 2)
        nav_ok = navigate_to_preferences(driver)
        if not nav_ok:
            log("  Navigation may have failed, but continuing anyway...")

        save_screenshot(driver, "preferences_page_loaded")

        # Step 3: Run all extraction strategies
        run_all_strategies(driver)

    except KeyboardInterrupt:
        log("\n  Interrupted by user.")
    except Exception as exc:
        log(f" FATAL ERROR: {exc}")
        log(traceback.format_exc())
        if driver:
            save_screenshot(driver, "fatal_error")
    finally:
        print_final_report()
        if driver:
            log("Closing browser...")
            try:
                driver.quit()
            except Exception:
                pass
        log("Done.")


if __name__ == "__main__":
    main()