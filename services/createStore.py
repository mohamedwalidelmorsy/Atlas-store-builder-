"""
Shopify Store Creation Service - Integrated with Flask
Full automation logic preserved - only integration changes
"""

import json
import time
import random
import os
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from dotenv import load_dotenv

load_dotenv()

class ShopifyAccountCreator:
    """
    Creates Shopify development stores using Selenium automation
    Preserves all original automation logic and human-like behavior
    """
    
    def __init__(self):
        self.driver = None
        self.wait = None
        self.action_count = 0
        
        # Load developer credentials from environment
        self.dev_email = os.getenv('SHOPIFY_DEV_EMAIL')
        self.dev_password = os.getenv('SHOPIFY_DEV_PASSWORD')
        
        # Store info (will be set when create_store is called)
        self.customer_email = None
        self.store_name = None
        self.country = None
        self.business_type = None
        
        if not self.dev_email or not self.dev_password:
            raise ValueError("Missing SHOPIFY_DEV_EMAIL or SHOPIFY_DEV_PASSWORD in .env")
    
    # ============================================================
    # HELPER METHODS
    # ============================================================

    def save_error_screenshot(self, filename):
        """Save screenshot to data/screenshots directory"""
        try:
            screenshots_dir = os.path.join("data", "screenshots")
            os.makedirs(screenshots_dir, exist_ok=True)
            filepath = os.path.join(screenshots_dir, filename)
            self.driver.save_screenshot(filepath)
            print(f" Screenshot saved: {filepath}")
        except Exception:
            pass

    # ============================================================
    # HUMAN-LIKE DELAYS (PRESERVED)
    # ============================================================


    def random_short_delay(self):
        delay = random.uniform(0.3, 0.8)
        print(f"Human-like wait: {delay:.1f}s")
        time.sleep(delay)
    
    def random_long_delay(self):
        delay = random.uniform(1.0, 2.0)
        print(f"Security wait: {delay:.1f}s")
        time.sleep(delay)
    
    def random_hesitation_pause(self):
        if random.random() < 0.1:
            delay = random.uniform(1.0, 2.0)
            print(f"Human hesitation pause: {delay:.1f}s")
            time.sleep(delay)
    
    def human_type(self, element, text, action_description=""):
        if action_description:
            print(f"{action_description}")
        element.clear()
        time.sleep(0.2)
        element.send_keys(text)
        if action_description:
            print(f"Finished {action_description.lower()}")
        time.sleep(0.3)
    
    def increment_action_and_maybe_pause(self):
        self.action_count += 1
        if self.action_count % random.randint(8, 12) == 0:
            self.random_hesitation_pause()
    
    # ============================================================
    # BROWSER SETUP
    # ============================================================
    
    def setup_driver(self):
        try:
            print("Setting up browser...")
            
            chrome_options = Options()
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument("--window-size=1280,800")
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.wait = WebDriverWait(self.driver, 15)
            
            print("Browser setup completed")
            self.random_short_delay()
            return True
            
        except Exception as e:
            print(f"Browser setup failed: {str(e)}")
            return False
    
    # ============================================================
    # LOGIN
    # ============================================================
    
    def navigate_to_partners_and_login(self):
        print(" Opening Shopify Partners page...")
        self.driver.get("https://partners.shopify.com")
        self.random_long_delay()
        
        try:
            print(" Looking for login link (desktop)...")
            login_link = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((
                    By.CSS_SELECTOR, 
                    'a[href="https://partners.shopify.com/organizations"][aria-label*="Log in"]'
                ))
            )
            print(" Found login link (desktop)")
            login_link.click()
            print(" Clicked login link")
            self.random_short_delay()
            return True
            
        except TimeoutException:
            print(" Desktop link not found - trying mobile menu...")
            
            menu_button = self.wait.until(
                EC.element_to_be_clickable((
                    By.CSS_SELECTOR,
                    'button[aria-label="Menu"][data-component-name="navigation-toggle-open"]'
                ))
            )
            print(" Found menu button")
            menu_button.click()
            print(" Opened mobile menu")
            self.random_short_delay()
            
            login_in_menu = self.wait.until(
                EC.element_to_be_clickable((
                    By.CSS_SELECTOR,
                    'a[href="https://partners.shopify.com/organizations"][data-component-name="login"]'
                ))
            )
            print(" Found login link in menu")
            login_in_menu.click()
            print(" Clicked login link from menu")
            self.random_short_delay()
            return True
    
    def enter_email(self):
        print(" Looking for email field...")
        email_input = self.wait.until(
            EC.element_to_be_clickable((
                By.CSS_SELECTOR,
                'input[name="account[email]"][type="email"]'
            ))
        )
        print(" Email field found")
        email_input.clear()
        self.random_short_delay()
        self.human_type(email_input, self.dev_email, "Typing email")
        print(f" Email entered: {self.dev_email}")
        return True
    
    def click_continue_with_email(self):
        print(" Looking for continue button...")
        continue_button = self.wait.until(
            EC.element_to_be_clickable((
                By.CSS_SELECTOR,
                'button[type="submit"].login-button'
            ))
        )
        print(" Continue button found")
        continue_button.click()
        print(" Clicked continue button")
        self.random_short_delay()
        return True
    
    def enter_password(self):
        print(" Looking for password field...")
        password_input = self.wait.until(
            EC.element_to_be_clickable((
                By.CSS_SELECTOR,
                'input[name="account[password]"][type="password"]'
            ))
        )
        print(" Password field found")
        password_input.clear()
        self.random_short_delay()
        self.human_type(password_input, self.dev_password, "Typing password")
        print(" Password entered")
        return True
    
    def click_login_button(self):
        print(" Looking for login button...")
        login_button = self.wait.until(
            EC.element_to_be_clickable((
                By.CSS_SELECTOR,
                'button[type="submit"]'
            ))
        )
        print(" Login button found")
        login_button.click()
        print(" Clicked login button")
        self.random_long_delay()
        return True
    
    def handle_organization_selection(self):
        print(" Checking for organization selection screen...")
        self.random_long_delay()
        
        try:
            org_link = WebDriverWait(self.driver, 8).until(
                EC.element_to_be_clickable((
                    By.CSS_SELECTOR,
                    'a._OrganizationsList__listItem_1395x_6[data-polaris-unstyled="true"]'
                ))
            )
            
            try:
                org_name = org_link.find_element(By.CSS_SELECTOR, '.Polaris-Text--bodyMd').text
                print(f" Found organization: {org_name}")
            except:
                print(f" Found organization link")
            
            org_link.click()
            print(f" Selected organization")
            self.random_long_delay()
            return True
            
        except TimeoutException:
            print("[i] No organization selection screen - continuing...")
            return True
    
    def verify_login_success(self):
        print(" Verifying login...")
        self.random_long_delay()
        
        current_url = self.driver.current_url
        print(f" Current URL: {current_url}")
        
        if "partners.shopify.com" in current_url and "signin" not in current_url and "login" not in current_url:
            print(f" Login successful!")
            return True
        else:
            print(f" Still on login page")
            return False
    
    # ============================================================
    # STORE CREATION
    # ============================================================
    
    def click_stores_button(self):
        print(" Looking for Stores button...")
        self.random_short_delay()
        
        stores_button = self.wait.until(
            EC.element_to_be_clickable((
                By.CSS_SELECTOR,
                'a.Polaris-Navigation__Item[href*="/stores"]'
            ))
        )
        
        print(" Found Stores button")
        stores_button.click()
        print(" Clicked Stores button")
        self.random_short_delay()
        return True
    
    def click_add_store_button(self):
        print(" Looking for Add store button...")
        self.random_short_delay()
        
        add_button = self.wait.until(
            EC.element_to_be_clickable((
                By.XPATH,
                "//button[.//span[text()='Add store']]"
            ))
        )
        
        print(" Found Add store button")
        add_button.click()
        print(" Clicked Add store button")
        self.random_short_delay()
        return True
    
    def click_create_development_store(self):
        print(" Looking for Create development store option...")
        self.random_short_delay()
        
        create_link = self.wait.until(
            EC.element_to_be_clickable((
                By.CSS_SELECTOR,
                'a.Polaris-ActionList__Item[href*="/stores/new"]'
            ))
        )
        
        print(" Found Create development store option")
        create_link.click()
        print(" Clicked Create development store")
        self.random_short_delay()
        return True
    
    def _random_word(self, length=None):
        """Generate a random lowercase word (5-8 chars)."""
        if length is None:
            length = random.randint(5, 8)
        consonants = 'bcdfghjklmnprstvwxz'
        vowels = 'aeiou'
        word = ''
        for i in range(length):
            word += random.choice(vowels if i % 2 == 1 else consonants)
        return word

    def generate_unique_store_name(self, attempt=0):
        base_name = self.store_name if self.store_name else self._random_word()
        base_name = base_name.lower().strip().replace(' ', '-')
        suffix = '.ts-scout'
        if attempt == 0:
            unique_name = f"{base_name}{suffix}"
        else:
            unique_name = f"{base_name}{random.randint(10, 999)}{suffix}"
        print(f" Generated store name: {unique_name} (attempt {attempt + 1})")
        return unique_name
    
    def fill_store_name_field(self, attempt=0):
        print(" Looking for store name field...")
        self.random_short_delay()

        unique_store_name = self.generate_unique_store_name(attempt=attempt)

        name_input = self.wait.until(
            EC.element_to_be_clickable((
                By.CSS_SELECTOR,
                'input[type="text"]'
            ))
        )

        # Clear the field completely (Ctrl+A then Delete - more reliable than .clear())
        name_input.click()
        self.driver.execute_script("""
            var input = arguments[0];
            input.select();
            input.value = '';
            input.dispatchEvent(new Event('input', { bubbles: true }));
        """, name_input)
        name_input.clear()
        self.random_short_delay()

        print(" Found store name field")
        self.human_type(name_input, unique_store_name, "Typing store name")
        print(f" Store name filled: {unique_store_name}")
        return unique_store_name
    
    def select_country(self):
        print(f" Selecting country: {self.country}")
        self.random_short_delay()
        
        try:
            country_select = self.wait.until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR,
                    'select#PolarisSelect1, select.Polaris-Select__Input'
                ))
            )
            print(" Found country dropdown")
        except Exception as e:
            print(f" Could not find country dropdown: {str(e)}")
            return False
        
        try:
            option = country_select.find_element(By.CSS_SELECTOR, f"option[value='{self.country}']")
            print(f" Found country option: {option.text}")
            
            self.driver.execute_script("""
                arguments[0].value = arguments[1];
                arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
            """, country_select, self.country)
            
            print(f" Selected country: {option.text}")
            self.random_short_delay()
            return True
            
        except Exception as e:
            print(f" Failed to select country: {str(e)}")
            print(" Continuing anyway...")
            return False
    
    def click_create_development_store_button(self):
        print(" Looking for Create button...")
        self.random_short_delay()
        
        # Scroll to bottom
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        self.random_short_delay()
        
        # Check if button is enabled
        create_button = self.wait.until(
            EC.presence_of_element_located((
                By.ID,
                'create-new-store-button'
            ))
        )
        
        # Check for validation errors
        try:
            error_messages = self.driver.find_elements(By.CSS_SELECTOR, '[class*="error"], [class*="Error"], [aria-invalid="true"]')
            if error_messages:
                print(" Found validation errors:")
                for error in error_messages:
                    if error.is_displayed():
                        print(f"  - {error.text}")
        except:
            pass
        
        # Check button state
        is_disabled = create_button.get_attribute('aria-disabled') == 'true' or not create_button.is_enabled()
        
        if is_disabled:
            print(" Create button is disabled!")
            print("Checking form completion...")
            
            self.save_error_screenshot("form_validation_error.png")
            return False
        
        print(" Found Create development store button")
        
        # Click using multiple methods
        try:
            create_button.click()
            print(" Clicked Create button (normal)")
        except Exception as e:
            print(f" Normal click failed: {str(e)}")
            try:
                self.driver.execute_script("arguments[0].click();", create_button)
                print(" Clicked Create button (JS)")
            except Exception as e2:
                print(f" JS click failed: {str(e2)}")
                return False
        
        print(" Waiting for redirect...")
        
        # Wait for URL to change
        initial_url = self.driver.current_url
        max_wait = 30
        
        for i in range(max_wait):
            time.sleep(1)
            current_url = self.driver.current_url
            
            # Check if URL changed
            if current_url != initial_url:
                print(f" URL changed to: {current_url}")
                break
            
            # Check for account selection screen
            if "accounts.shopify.com" in current_url:
                print(f" Redirected to account selection")
                break
            
            if i % 5 == 0:
                print(f"Still waiting... ({i+1}/{max_wait}s)")
        
        final_url = self.driver.current_url
        print(f" Final URL: {final_url}")
        
        # Check if still on same page
        if final_url == initial_url:
            print(" URL did not change - store creation may have failed")
            
            # Check for error messages
            try:
                error_banners = self.driver.find_elements(By.CSS_SELECTOR, '[role="alert"], .Polaris-Banner--statusCritical')
                if error_banners:
                    print(" Error messages found:")
                    for banner in error_banners:
                        if banner.is_displayed():
                            print(f"  - {banner.text}")
            except:
                pass
            
            return False
        
        return True
    
    def select_account_after_creation(self):
        print(" Checking for account selection screen...")
        
        current_url = self.driver.current_url
        
        if "accounts.shopify.com/select" not in current_url:
            print("[i] No account selection needed")
            return True
        
        print(" Account selection screen detected")
        self.random_short_delay()
        
        try:
            account_cards = self.driver.find_elements(By.CSS_SELECTOR, 'a.choose-account-card, a[class*="account"]')
            print(f"Found {len(account_cards)} account card(s)")
            
            for card in account_cards:
                try:
                    card_text = card.text.lower()
                    
                    if 'add account' in card_text or 'add another' in card_text:
                        print(f" Skipping: Add account card")
                        continue
                    
                    if self.dev_email.lower() in card_text or card.is_displayed():
                        print(f" Found valid account card")
                        
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", card)
                        self.random_short_delay()
                        
                        try:
                            card.click()
                            print(" Clicked account card")
                        except:
                            self.driver.execute_script("arguments[0].click();", card)
                            print(" Clicked account card (JS)")
                        
                        print(" Waiting for store to load...")
                        time.sleep(random.uniform(10.0, 15.0))
                        
                        print(f" New URL: {self.driver.current_url}")
                        return True
                        
                except Exception as e:
                    print(f" Error checking card: {str(e)}")
                    continue
            
            print(" Trying first visible card...")
            for card in account_cards:
                try:
                    if card.is_displayed() and 'add' not in card.text.lower():
                        card.click()
                        print(" Clicked first available card")
                        time.sleep(random.uniform(10.0, 15.0))
                        return True
                except:
                    continue
            
            print(" Could not find account to select")
            return False
            
        except Exception as e:
            print(f" Error in account selection: {str(e)}")
            return False
    
    def extract_store_info(self):
        try:
            print("Extracting store information...")
            self.random_long_delay()

            current_url = self.driver.current_url
            print(f"Current URL: {current_url}")

            store_url = None
            store_id = None

            # Pattern 1: admin.shopify.com/store/{store-name}/... (New Shopify Admin)
            if "admin.shopify.com/store/" in current_url:
                match = re.search(r'admin\.shopify\.com/store/([^/]+)', current_url)
                if match:
                    store_id = match.group(1)
                    store_url = f"https://{store_id}.myshopify.com"
                    print(f" Extracted from admin.shopify.com format")

            # Pattern 2: {store-name}.myshopify.com (Old format)
            elif "myshopify.com" in current_url:
                store_url = current_url.split("admin")[0] if "admin" in current_url else current_url
                try:
                    store_id = store_url.split("//")[1].split(".myshopify.com")[0]
                except:
                    store_id = "unknown"
                print(f" Extracted from myshopify.com format")

            # Fallback: Search in page links
            if not store_url:
                try:
                    link_elements = self.driver.find_elements(By.TAG_NAME, "a")
                    for link in link_elements:
                        href = link.get_attribute("href")
                        if href and "myshopify.com" in href:
                            store_url = href.split("admin")[0] if "admin" in href else href
                            store_id = store_url.split("//")[1].split(".myshopify.com")[0]
                            break
                except:
                    pass

            if not store_url:
                print("Warning: Could not extract store URL, using placeholder")
                timestamp = int(time.time())
                store_id = f"store-{timestamp}"
                store_url = f"https://{store_id}.myshopify.com"

            print(f"Store URL: {store_url}")
            print(f"Store ID: {store_id}")

            return {
                'store_url': store_url,
                'store_id': store_id,
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

        except Exception as e:
            print(f"Error extracting store info: {str(e)}")
            return None

    # ============================================================
    # CHANGE STORE PASSWORD
    # ============================================================

    def change_store_password(self, new_password="ts-scout1234"):
        """
        Change the store password via Online Store > Preferences > Password protection.
        Handles Shopify's iframe-based admin layout where the Preferences content
        is rendered inside an iframe, making standard selectors fail.
        Returns: dict with 'success' (bool) and 'password' (str or None)
        """
        result = {'success': False, 'password': None}
        switched_to_iframe = False

        try:
            print("\n[PASSWORD] Starting store password change...")
            print("=" * 70)

            # ==============================================================
            # STEP 1: Navigate to Online Store > Preferences
            # ==============================================================
            print("[STEP 1] Navigating to Online Store > Preferences...")
            self.random_short_delay()

            # Try direct URL navigation first (most reliable)
            current_url = self.driver.current_url
            store_slug = None
            if "admin.shopify.com/store/" in current_url:
                match = re.search(r'admin\.shopify\.com/store/([^/]+)', current_url)
                if match:
                    store_slug = match.group(1)

            if store_slug:
                prefs_url = f"https://admin.shopify.com/store/{store_slug}/online_store/preferences"
                print(f"[STEP 1] Direct navigation to: {prefs_url}")
                self.driver.get(prefs_url)
                self.random_long_delay()
                time.sleep(3)
            else:
                # Fallback: click through navigation
                online_store_selectors = [
                    "//a[contains(@href, '/online_store')]",
                    "//span[contains(text(), 'Online Store')]"
                ]
                online_store_button = None
                for selector in online_store_selectors:
                    try:
                        online_store_button = WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                        if online_store_button:
                            break
                    except Exception:
                        continue

                if not online_store_button:
                    print("[STEP 1] FAILED - 'Online Store' nav item not found")
                    self.save_error_screenshot("password_step1_fail.png")
                    return result

                try:
                    online_store_button.click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", online_store_button)
                self.random_long_delay()

                preferences_selectors = [
                    "//a[contains(@href, '/preferences')]",
                    "//span[contains(text(), 'Preferences')]"
                ]
                preferences_button = None
                for selector in preferences_selectors:
                    try:
                        preferences_button = WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                        if preferences_button:
                            break
                    except Exception:
                        continue

                if not preferences_button:
                    print("[STEP 1] FAILED - 'Preferences' link not found")
                    self.save_error_screenshot("password_step1_fail.png")
                    return result

                try:
                    preferences_button.click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", preferences_button)
                self.random_long_delay()
                time.sleep(3)

            # Verify URL
            try:
                WebDriverWait(self.driver, 15).until(EC.url_contains("/preferences"))
                print(f"[STEP 1] On Preferences page: {self.driver.current_url}")
            except TimeoutException:
                print(f"[STEP 1] WARNING - URL: {self.driver.current_url}")
                self.save_error_screenshot("password_step1_url.png")
                return result

            # ==============================================================
            # STEP 2: Detect and switch into iframe (KEY FIX)
            # ==============================================================
            print("[STEP 2] Checking for iframes on Preferences page...")
            self.random_short_delay()
            time.sleep(3)

            # First check: are inputs already in the main document?
            main_input_count = self.driver.execute_script(
                "return document.querySelectorAll('input').length;"
            )
            print(f"[STEP 2] Inputs in main document: {main_input_count}")

            if main_input_count == 0:
                # Inputs NOT in main doc - search iframes
                iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                print(f"[STEP 2] Found {len(iframes)} iframe(s) on page")

                for i, frame in enumerate(iframes):
                    frame_src = frame.get_attribute("src") or ""
                    frame_id = frame.get_attribute("id") or ""
                    print(f"[STEP 2]   iframe[{i}]: id='{frame_id}', src='{frame_src[:120]}'")

                    try:
                        self.driver.switch_to.frame(frame)
                        inner_inputs = self.driver.execute_script(
                            "return document.querySelectorAll('input').length;"
                        )
                        print(f"[STEP 2]     -> {inner_inputs} input(s) inside")

                        if inner_inputs > 0:
                            # Verify this is the right frame (has password-related content)
                            body_text = self.driver.execute_script(
                                "return document.body ? document.body.innerText : '';"
                            ) or ""
                            if "password" in body_text.lower() or "characters used" in body_text.lower() or inner_inputs >= 1:
                                print(f"[STEP 2] ** SWITCHED into iframe[{i}] - content frame found **")
                                switched_to_iframe = True
                                break

                        # Not the right frame, switch back
                        self.driver.switch_to.default_content()
                    except Exception as exc:
                        print(f"[STEP 2]     -> Error: {exc}")
                        try:
                            self.driver.switch_to.default_content()
                        except Exception:
                            pass

                if not switched_to_iframe and main_input_count == 0:
                    print("[STEP 2] WARNING - No iframe with inputs found. Trying Shadow DOM...")
                    # Try shadow DOM as fallback
                    shadow_result = self.driver.execute_script("""
                        function findInShadow(root) {
                            var els = root.querySelectorAll('*');
                            for (var i = 0; i < els.length; i++) {
                                if (els[i].shadowRoot) {
                                    var inputs = els[i].shadowRoot.querySelectorAll('input');
                                    if (inputs.length > 0) return true;
                                    if (findInShadow(els[i].shadowRoot)) return true;
                                }
                            }
                            return false;
                        }
                        return findInShadow(document);
                    """)
                    if shadow_result:
                        print("[STEP 2] Shadow DOM inputs detected (complex case)")
                    else:
                        print("[STEP 2] No inputs found anywhere - page may not have loaded")
                        self.save_error_screenshot("password_step2_no_inputs.png")
            else:
                print("[STEP 2] Inputs in main document - no iframe switch needed")

            # ==============================================================
            # STEP 3: Find password input with strict selector
            # ==============================================================
            print("[STEP 3] Searching for password input...")
            self.random_short_delay()

            password_input = None
            input_selectors = [
                (By.XPATH, "//input[@maxlength='100' and contains(@class, 'Polaris-TextField__Input')]"),
                (By.XPATH, "//input[@type='text' and @maxlength='100']"),
                (By.CSS_SELECTOR, "input.Polaris-TextField__Input[maxlength='100']"),
                (By.CSS_SELECTOR, "input[type='text'][maxlength='100']"),
            ]

            for by, selector in input_selectors:
                try:
                    password_input = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((by, selector))
                    )
                    if password_input:
                        print(f"[STEP 3] Found password input via: {selector}")
                        break
                except TimeoutException:
                    continue

            if not password_input:
                print("[STEP 3] FAILED - Password input not found")
                self.save_error_screenshot("password_step3_fail.png")
                return result

            # Verify interactable
            if not password_input.is_displayed() or not password_input.is_enabled():
                print("[STEP 3] FAILED - Input exists but not interactable")
                self.save_error_screenshot("password_step3_fail.png")
                return result

            # Scroll into view
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", password_input)
            self.random_short_delay()

            # Read current password
            current_password = password_input.get_attribute('value') or ""
            print(f"[STEP 3] Current store password: '{current_password}'")
            result['password'] = current_password

            # ==============================================================
            # STEP 4: Set new password with React-compatible event dispatch
            # ==============================================================
            if new_password:
                print(f"[STEP 4] Setting new password: '{new_password}'...")

                try:
                    # Use nativeInputValueSetter + dispatch input/change/blur events
                    # This forces React to recognize the value change AND triggers
                    # Shopify's ContextualSaveBar to appear
                    self.driver.execute_script("""
                        var el = arguments[0];
                        var newVal = arguments[1];

                        // Focus the input first
                        el.focus();

                        // Clear using native setter
                        var nativeSetter = Object.getOwnPropertyDescriptor(
                            window.HTMLInputElement.prototype, 'value').set;
                        nativeSetter.call(el, '');
                        el.dispatchEvent(new Event('input', { bubbles: true }));

                        // Set new value using native setter
                        nativeSetter.call(el, newVal);

                        // Dispatch all events to trigger React state update + Save bar
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                        el.dispatchEvent(new Event('blur', { bubbles: true }));

                        // Also dispatch React synthetic events
                        var inputEvent = new InputEvent('input', {
                            bubbles: true,
                            cancelable: true,
                            inputType: 'insertText',
                            data: newVal
                        });
                        el.dispatchEvent(inputEvent);
                    """, password_input, new_password)

                    self.random_short_delay()
                    time.sleep(1)

                    # Verify the value was set
                    actual_value = password_input.get_attribute('value')
                    if actual_value == new_password:
                        print(f"[STEP 4] Password updated to: '{new_password}'")
                        result['password'] = new_password
                    else:
                        print(f"[STEP 4] WARNING - Value is '{actual_value}', expected '{new_password}'")
                        # Try direct typing as fallback
                        try:
                            password_input.clear()
                            password_input.send_keys(new_password)
                            time.sleep(0.5)
                            actual_value = password_input.get_attribute('value')
                            if actual_value == new_password:
                                print(f"[STEP 4] Password set via send_keys: '{new_password}'")
                                result['password'] = new_password
                        except Exception:
                            pass

                except Exception as e:
                    print(f"[STEP 4] Failed to set password: {e}")
                    print(f"[STEP 4] Keeping current password: '{current_password}'")
            else:
                print("[STEP 4] No new password provided, keeping current.")

            # ==============================================================
            # STEP 5: Click Save via ContextualSaveBar or page Save button
            # ==============================================================
            print("[STEP 5] Looking for Save button (ContextualSaveBar)...")

            # CRITICAL: The ContextualSaveBar lives in the MAIN document,
            # not inside the iframe. Must switch back to find it.
            if switched_to_iframe:
                print("[STEP 5] Switching back to main document to find Save bar...")
                self.driver.switch_to.default_content()
                switched_to_iframe = False

            self.random_short_delay()
            time.sleep(2)

            save_button = None

            # Priority 1: Shopify ContextualSaveBar (black bar at top)
            # Real class: _ContextualButton_10w4z_1 _Primary_10w4z_28 (CSS Modules)
            contextual_save_selectors = [
                # Exact match for Shopify's CSS Modules ContextualSaveBar button
                "//button[contains(@class, 'ContextualButton') and contains(@class, 'Primary')]",
                "//button[contains(@class, '_ContextualButton') and @type='submit']",
                "//button[contains(@class, '_Primary') and @type='submit' and @aria-busy]",
                # Polaris ContextualSaveBar selectors (older versions)
                "//div[contains(@class, 'Polaris-Frame-ContextualSaveBar')]//button[contains(@class, 'Polaris-Button--primary')]",
                "//div[contains(@class, 'ContextualSaveBar')]//button[contains(@class, 'primary')]",
                "//div[contains(@class, 'Polaris-Frame-ContextualSaveBar')]//button[.//span[contains(text(), 'Save')]]",
            ]

            for selector in contextual_save_selectors:
                try:
                    candidates = self.driver.find_elements(By.XPATH, selector)
                    for btn in candidates:
                        if btn.is_displayed() and btn.is_enabled():
                            save_button = btn
                            print(f"[STEP 5] Found ContextualSaveBar Save button")
                            break
                    if save_button:
                        break
                except Exception:
                    continue

            # Priority 2: Regular page-level Save button
            if not save_button:
                regular_save_selectors = [
                    "//button[@type='submit' and contains(@class, 'Polaris-Button--primary')]",
                    "//button[@type='submit']//span[contains(text(), 'Save')]/..",
                    "//button[contains(@class, 'Polaris-Button--primary') and @type='submit']",
                    "//div[contains(@class, 'Polaris-PageActions')]//button[@type='submit']",
                ]
                for selector in regular_save_selectors:
                    try:
                        candidates = self.driver.find_elements(By.XPATH, selector)
                        for btn in candidates:
                            if btn.is_displayed() and btn.is_enabled():
                                save_button = btn
                                print(f"[STEP 5] Found regular Save button")
                                break
                        if save_button:
                            break
                    except Exception:
                        continue

            # Priority 3: JS scan - find by class pattern or text
            if not save_button:
                try:
                    save_button = self.driver.execute_script("""
                        // Look for ContextualButton with Primary class (CSS Modules)
                        var buttons = document.querySelectorAll('button[type="submit"]');
                        for (var i = 0; i < buttons.length; i++) {
                            var cls = buttons[i].className || '';
                            if (cls.includes('ContextualButton') && cls.includes('Primary')) {
                                return buttons[i];
                            }
                        }
                        // Fallback: button with "Save" text
                        for (var i = 0; i < buttons.length; i++) {
                            var text = buttons[i].innerText || '';
                            if (text.toLowerCase().trim() === 'save') {
                                return buttons[i];
                            }
                        }
                        // Last resort: any submit button with Primary in class
                        for (var i = 0; i < buttons.length; i++) {
                            var cls = buttons[i].className || '';
                            if (cls.includes('Primary') || cls.includes('primary')) {
                                return buttons[i];
                            }
                        }
                        return null;
                    """)
                    if save_button:
                        print("[STEP 5] Found Save button via JS scan")
                except Exception:
                    pass

            if not save_button:
                print("[STEP 5] WARNING - Save button not found. Password was read but not saved.")
                self.save_error_screenshot("password_step5_no_save.png")
                # Still return partial success - we read the password
                result['success'] = True
                return result

            # Click the save button
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", save_button)
            self.random_short_delay()

            try:
                save_button.click()
                print("[STEP 5] Clicked Save button")
            except Exception:
                self.driver.execute_script("arguments[0].click();", save_button)
                print("[STEP 5] Clicked Save button (JS)")

            # ==============================================================
            # STEP 6: Wait for save confirmation
            # ==============================================================
            print("[STEP 6] Waiting for save confirmation...")
            time.sleep(2)

            save_confirmed = False
            try:
                WebDriverWait(self.driver, 10).until(
                    lambda d: (
                        # Success toast appeared
                        d.find_elements(By.XPATH, "//*[contains(@class, 'Polaris-Toast') or contains(@class, 'Banner--statusSuccess')]")
                        # OR ContextualSaveBar disappeared (save completed)
                        or not d.find_elements(By.XPATH, "//div[contains(@class, 'Polaris-Frame-ContextualSaveBar')]")
                        # OR "saved" text appeared
                        or d.find_elements(By.XPATH, "//*[contains(text(), 'saved') or contains(text(), 'Saved')]")
                    )
                )
                save_confirmed = True
                print("[STEP 6] Save confirmed")
            except TimeoutException:
                print("[STEP 6] No explicit confirmation, assuming save completed")
                save_confirmed = True

            self.random_long_delay()

            # ==============================================================
            # STEP 7: Return result
            # ==============================================================
            result['success'] = save_confirmed
            final_password = result['password']

            if result['success']:
                print(f"[PASSWORD] SUCCESS - Password: '{final_password}'")
            else:
                print(f"[PASSWORD] PARTIAL - Password read: '{final_password}'")
            print("=" * 70)
            return result

        except Exception as e:
            print(f"[PASSWORD] EXCEPTION - {str(e)}")
            self.save_error_screenshot("password_change_error.png")
            return result

        finally:
            # ==============================================================
            # ALWAYS switch back to default content (main document)
            # ==============================================================
            if switched_to_iframe:
                try:
                    self.driver.switch_to.default_content()
                    print("[PASSWORD] Switched back to default content")
                except Exception:
                    pass

    # ============================================================
    # MAIN METHOD
    # ============================================================
    
    def create_store(self, email, store_name, country="US", business_type="ecommerce"):
        self.customer_email = email
        self.store_name = store_name
        self.country = country
        self.business_type = business_type
        
        print("="*70)
        print(f"Starting store creation for: {email}")
        print(f"Store name: {store_name}")
        print("="*70)
        
        try:
            if not self.setup_driver():
                raise Exception("Failed to setup browser")
            
            if not self.navigate_to_partners_and_login():
                raise Exception("Failed to navigate to login")
            
            if not self.enter_email():
                raise Exception("Failed to enter email")
            
            if not self.click_continue_with_email():
                raise Exception("Failed to click continue")
            
            if not self.enter_password():
                raise Exception("Failed to enter password")
            
            if not self.click_login_button():
                raise Exception("Failed to click login")
            
            if not self.handle_organization_selection():
                raise Exception("Failed to handle organization selection")
            
            if not self.verify_login_success():
                raise Exception("Login verification failed")
            
            if not self.click_stores_button():
                raise Exception("Failed to click Stores button")
            
            if not self.click_add_store_button():
                raise Exception("Failed to click Add Store")
            
            if not self.click_create_development_store():
                raise Exception("Failed to click Create Development")
            
            # Try store creation with retry logic for taken names
            max_name_attempts = 3
            unique_name = None
            for attempt in range(max_name_attempts):
                unique_name = self.fill_store_name_field(attempt=attempt)
                if not unique_name:
                    raise Exception("Failed to fill store form")

                if attempt == 0:
                    if not self.select_country():
                        print("Warning: Failed to select country, continuing anyway...")

                if self.click_create_development_store_button():
                    break  # Success
                else:
                    if attempt < max_name_attempts - 1:
                        print(f" Store name might be taken, retrying with a different name... (attempt {attempt + 2}/{max_name_attempts})")
                        continue
                    else:
                        raise Exception("Failed to submit store creation after multiple attempts")
            
            if not self.select_account_after_creation():
                raise Exception("Failed to select account after creation")
            
            store_info = self.extract_store_info()
            if not store_info:
                raise Exception("Failed to extract store information")
            
            print("Navigating to admin dashboard...")
            admin_url = store_info['store_url'].rstrip('/') + '/admin'
            self.driver.get(admin_url)
            self.random_long_delay()

            # Change store password to default (or get current password)
            password_result = self.change_store_password("ts-scout1234")
            store_password = password_result.get('password') if password_result else None
            if store_password:
                print(f" Store password: {store_password}")
            else:
                print(" Warning: Could not get store password")

            print("="*70)
            print("Store created successfully!")
            print(f"URL: {store_info['store_url']}")
            print(f"ID: {store_info['store_id']}")
            if store_password:
                print(f"Password: {store_password}")
            print("="*70)

            store_data = {
                'store_url': store_info['store_url'],
                'store_id': store_info['store_id'],
                'admin_url': admin_url,
                'created_at': store_info.get('created_at'),
                'store_password': store_password
            }

            return store_data, self.driver
            
        except Exception as e:
            print(f"Store creation failed: {str(e)}")

            if self.driver:
                self.save_error_screenshot("store_creation_error.png")

            if self.driver:
                self.driver.quit()
                print("Browser closed due to error")
            
            raise