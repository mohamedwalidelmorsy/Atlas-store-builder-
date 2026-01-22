"""
Shopify Store Creation Service - Integrated with Flask
Full automation logic preserved - only integration changes
"""

import json
import time
import random
import os
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
        print("🌐 Opening Shopify Partners page...")
        self.driver.get("https://partners.shopify.com")
        self.random_long_delay()
        
        try:
            print("🔍 Looking for login link (desktop)...")
            login_link = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((
                    By.CSS_SELECTOR, 
                    'a[href="https://partners.shopify.com/organizations"][aria-label*="Log in"]'
                ))
            )
            print("✅ Found login link (desktop)")
            login_link.click()
            print("✅ Clicked login link")
            self.random_short_delay()
            return True
            
        except TimeoutException:
            print("📱 Desktop link not found - trying mobile menu...")
            
            menu_button = self.wait.until(
                EC.element_to_be_clickable((
                    By.CSS_SELECTOR,
                    'button[aria-label="Menu"][data-component-name="navigation-toggle-open"]'
                ))
            )
            print("✅ Found menu button")
            menu_button.click()
            print("✅ Opened mobile menu")
            self.random_short_delay()
            
            login_in_menu = self.wait.until(
                EC.element_to_be_clickable((
                    By.CSS_SELECTOR,
                    'a[href="https://partners.shopify.com/organizations"][data-component-name="login"]'
                ))
            )
            print("✅ Found login link in menu")
            login_in_menu.click()
            print("✅ Clicked login link from menu")
            self.random_short_delay()
            return True
    
    def enter_email(self):
        print("📧 Looking for email field...")
        email_input = self.wait.until(
            EC.element_to_be_clickable((
                By.CSS_SELECTOR,
                'input[name="account[email]"][type="email"]'
            ))
        )
        print("✅ Email field found")
        email_input.clear()
        self.random_short_delay()
        self.human_type(email_input, self.dev_email, "Typing email")
        print(f"✅ Email entered: {self.dev_email}")
        return True
    
    def click_continue_with_email(self):
        print("🔘 Looking for continue button...")
        continue_button = self.wait.until(
            EC.element_to_be_clickable((
                By.CSS_SELECTOR,
                'button[type="submit"].login-button'
            ))
        )
        print("✅ Continue button found")
        continue_button.click()
        print("✅ Clicked continue button")
        self.random_short_delay()
        return True
    
    def enter_password(self):
        print("🔐 Looking for password field...")
        password_input = self.wait.until(
            EC.element_to_be_clickable((
                By.CSS_SELECTOR,
                'input[name="account[password]"][type="password"]'
            ))
        )
        print("✅ Password field found")
        password_input.clear()
        self.random_short_delay()
        self.human_type(password_input, self.dev_password, "Typing password")
        print("✅ Password entered")
        return True
    
    def click_login_button(self):
        print("🔘 Looking for login button...")
        login_button = self.wait.until(
            EC.element_to_be_clickable((
                By.CSS_SELECTOR,
                'button[type="submit"]'
            ))
        )
        print("✅ Login button found")
        login_button.click()
        print("✅ Clicked login button")
        self.random_long_delay()
        return True
    
    def handle_organization_selection(self):
        print("🏢 Checking for organization selection screen...")
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
                print(f"✅ Found organization: {org_name}")
            except:
                print(f"✅ Found organization link")
            
            org_link.click()
            print(f"✅ Selected organization")
            self.random_long_delay()
            return True
            
        except TimeoutException:
            print("ℹ️ No organization selection screen - continuing...")
            return True
    
    def verify_login_success(self):
        print("✅ Verifying login...")
        self.random_long_delay()
        
        current_url = self.driver.current_url
        print(f"📍 Current URL: {current_url}")
        
        if "partners.shopify.com" in current_url and "signin" not in current_url and "login" not in current_url:
            print(f"✅ Login successful!")
            return True
        else:
            print(f"❌ Still on login page")
            return False
    
    # ============================================================
    # STORE CREATION
    # ============================================================
    
    def click_stores_button(self):
        print("🏪 Looking for Stores button...")
        self.random_short_delay()
        
        stores_button = self.wait.until(
            EC.element_to_be_clickable((
                By.CSS_SELECTOR,
                'a.Polaris-Navigation__Item[href*="/stores"]'
            ))
        )
        
        print("✅ Found Stores button")
        stores_button.click()
        print("✅ Clicked Stores button")
        self.random_short_delay()
        return True
    
    def click_add_store_button(self):
        print("➕ Looking for Add store button...")
        self.random_short_delay()
        
        add_button = self.wait.until(
            EC.element_to_be_clickable((
                By.XPATH,
                "//button[.//span[text()='Add store']]"
            ))
        )
        
        print("✅ Found Add store button")
        add_button.click()
        print("✅ Clicked Add store button")
        self.random_short_delay()
        return True
    
    def click_create_development_store(self):
        print("🔨 Looking for Create development store option...")
        self.random_short_delay()
        
        create_link = self.wait.until(
            EC.element_to_be_clickable((
                By.CSS_SELECTOR,
                'a.Polaris-ActionList__Item[href*="/stores/new"]'
            ))
        )
        
        print("✅ Found Create development store option")
        create_link.click()
        print("✅ Clicked Create development store")
        self.random_short_delay()
        return True
    
    def generate_unique_store_name(self):
        base_name = self.store_name if self.store_name else 'store'
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        unique_name = f"{base_name}-{timestamp}"
        print(f"📝 Generated store name: {unique_name}")
        return unique_name
    
    def fill_store_name_field(self):
        print("📝 Looking for store name field...")
        self.random_short_delay()
        
        unique_store_name = self.generate_unique_store_name()
        
        name_input = self.wait.until(
            EC.element_to_be_clickable((
                By.CSS_SELECTOR,
                'input[type="text"]'
            ))
        )
        
        print("✅ Found store name field")
        self.human_type(name_input, unique_store_name, "Typing store name")
        print(f"✅ Store name filled: {unique_store_name}")
        return unique_store_name
    
    def select_country(self):
        print(f"🌍 Selecting country: {self.country}")
        self.random_short_delay()
        
        try:
            country_select = self.wait.until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR,
                    'select#PolarisSelect1, select.Polaris-Select__Input'
                ))
            )
            print("✅ Found country dropdown")
        except Exception as e:
            print(f"❌ Could not find country dropdown: {str(e)}")
            return False
        
        try:
            option = country_select.find_element(By.CSS_SELECTOR, f"option[value='{self.country}']")
            print(f"✅ Found country option: {option.text}")
            
            self.driver.execute_script("""
                arguments[0].value = arguments[1];
                arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
            """, country_select, self.country)
            
            print(f"✅ Selected country: {option.text}")
            self.random_short_delay()
            return True
            
        except Exception as e:
            print(f"❌ Failed to select country: {str(e)}")
            print("⚠️ Continuing anyway...")
            return False
    
    def click_create_development_store_button(self):
        print("🚀 Looking for Create button...")
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
                print("⚠️ Found validation errors:")
                for error in error_messages:
                    if error.is_displayed():
                        print(f"  - {error.text}")
        except:
            pass
        
        # Check button state
        is_disabled = create_button.get_attribute('aria-disabled') == 'true' or not create_button.is_enabled()
        
        if is_disabled:
            print("⚠️ Create button is disabled!")
            print("Checking form completion...")
            
            # Try to take screenshot
            try:
                self.driver.save_screenshot("form_validation_error.png")
                print("Screenshot saved: form_validation_error.png")
            except:
                pass
            
            return False
        
        print("✅ Found Create development store button")
        
        # Click using multiple methods
        try:
            create_button.click()
            print("✅ Clicked Create button (normal)")
        except Exception as e:
            print(f"⚠️ Normal click failed: {str(e)}")
            try:
                self.driver.execute_script("arguments[0].click();", create_button)
                print("✅ Clicked Create button (JS)")
            except Exception as e2:
                print(f"❌ JS click failed: {str(e2)}")
                return False
        
        print("⏳ Waiting for redirect...")
        
        # Wait for URL to change
        initial_url = self.driver.current_url
        max_wait = 30
        
        for i in range(max_wait):
            time.sleep(1)
            current_url = self.driver.current_url
            
            # Check if URL changed
            if current_url != initial_url:
                print(f"✅ URL changed to: {current_url}")
                break
            
            # Check for account selection screen
            if "accounts.shopify.com" in current_url:
                print(f"✅ Redirected to account selection")
                break
            
            if i % 5 == 0:
                print(f"Still waiting... ({i+1}/{max_wait}s)")
        
        final_url = self.driver.current_url
        print(f"📍 Final URL: {final_url}")
        
        # Check if still on same page
        if final_url == initial_url:
            print("❌ URL did not change - store creation may have failed")
            
            # Check for error messages
            try:
                error_banners = self.driver.find_elements(By.CSS_SELECTOR, '[role="alert"], .Polaris-Banner--statusCritical')
                if error_banners:
                    print("⚠️ Error messages found:")
                    for banner in error_banners:
                        if banner.is_displayed():
                            print(f"  - {banner.text}")
            except:
                pass
            
            return False
        
        return True
    
    def select_account_after_creation(self):
        print("🔍 Checking for account selection screen...")
        
        current_url = self.driver.current_url
        
        if "accounts.shopify.com/select" not in current_url:
            print("ℹ️ No account selection needed")
            return True
        
        print("✅ Account selection screen detected")
        self.random_short_delay()
        
        try:
            account_cards = self.driver.find_elements(By.CSS_SELECTOR, 'a.choose-account-card, a[class*="account"]')
            print(f"Found {len(account_cards)} account card(s)")
            
            for card in account_cards:
                try:
                    card_text = card.text.lower()
                    
                    if 'add account' in card_text or 'add another' in card_text:
                        print(f"⏭️ Skipping: Add account card")
                        continue
                    
                    if self.dev_email.lower() in card_text or card.is_displayed():
                        print(f"✅ Found valid account card")
                        
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", card)
                        self.random_short_delay()
                        
                        try:
                            card.click()
                            print("✅ Clicked account card")
                        except:
                            self.driver.execute_script("arguments[0].click();", card)
                            print("✅ Clicked account card (JS)")
                        
                        print("⏳ Waiting for store to load...")
                        time.sleep(random.uniform(10.0, 15.0))
                        
                        print(f"📍 New URL: {self.driver.current_url}")
                        return True
                        
                except Exception as e:
                    print(f"⚠️ Error checking card: {str(e)}")
                    continue
            
            print("⚠️ Trying first visible card...")
            for card in account_cards:
                try:
                    if card.is_displayed() and 'add' not in card.text.lower():
                        card.click()
                        print("✅ Clicked first available card")
                        time.sleep(random.uniform(10.0, 15.0))
                        return True
                except:
                    continue
            
            print("❌ Could not find account to select")
            return False
            
        except Exception as e:
            print(f"❌ Error in account selection: {str(e)}")
            return False
    
    def extract_store_info(self):
        try:
            print("Extracting store information...")
            self.random_long_delay()
            
            current_url = self.driver.current_url
            print(f"Current URL: {current_url}")
            
            store_url = None
            store_id = None
            
            if "myshopify.com" in current_url:
                store_url = current_url.split("admin")[0] if "admin" in current_url else current_url
                
            if not store_url:
                try:
                    link_elements = self.driver.find_elements(By.TAG_NAME, "a")
                    for link in link_elements:
                        href = link.get_attribute("href")
                        if href and "myshopify.com" in href:
                            store_url = href.split("admin")[0] if "admin" in href else href
                            break
                except:
                    pass
            
            if store_url:
                try:
                    store_id = store_url.split("//")[1].split(".myshopify.com")[0]
                except:
                    store_id = "unknown"
            
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

    def change_store_password(self, new_password="1234"):
        """
        Change the store password to a default password
        Steps:
        1. Click on "Online Store" in navigation
        2. Click on "Preferences"
        3. Clear and enter new password in password field
        4. Click Save button
        """
        try:
            print("\n🔐 Changing store password...")
            print("="*70)

            # Step 1: Click "Online Store" in navigation
            print("📦 Step 1: Looking for 'Online Store' navigation item...")
            self.random_short_delay()

            online_store_selectors = [
                "//span[@class='Polaris-Navigation__Text Polaris-Navigation__Text--truncated']//span[contains(text(), 'Online Store')]",
                "//span[contains(@class, 'Polaris-Navigation__Text')]//span[contains(text(), 'Online Store')]",
                "//a[contains(@href, '/themes')]//span[contains(text(), 'Online Store')]"
            ]

            online_store_button = None
            for selector in online_store_selectors:
                try:
                    online_store_button = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    if online_store_button:
                        print("✅ Found 'Online Store' button")
                        break
                except Exception:
                    continue

            if not online_store_button:
                print("❌ Could not find 'Online Store' button")
                return False

            # Click Online Store
            try:
                online_store_button.click()
                print("✅ Clicked 'Online Store'")
            except Exception:
                self.driver.execute_script("arguments[0].click();", online_store_button)
                print("✅ Clicked 'Online Store' (JS)")

            self.random_long_delay()

            # Step 2: Click "Preferences"
            print("⚙️ Step 2: Looking for 'Preferences' option...")
            self.random_short_delay()

            preferences_selectors = [
                "//span[@class='Polaris-Navigation__Text Polaris-Navigation__Text--truncated']//span[contains(text(), 'Preferences')]",
                "//span[contains(@class, 'Polaris-Navigation__Text')]//span[contains(text(), 'Preferences')]",
                "//a[contains(@href, '/preferences')]//span[contains(text(), 'Preferences')]"
            ]

            preferences_button = None
            for selector in preferences_selectors:
                try:
                    preferences_button = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    if preferences_button:
                        print("✅ Found 'Preferences' button")
                        break
                except Exception:
                    continue

            if not preferences_button:
                print("❌ Could not find 'Preferences' button")
                return False

            # Click Preferences
            try:
                preferences_button.click()
                print("✅ Clicked 'Preferences'")
            except Exception:
                self.driver.execute_script("arguments[0].click();", preferences_button)
                print("✅ Clicked 'Preferences' (JS)")

            self.random_long_delay()

            # Step 3: Find and fill password field
            print(f"🔑 Step 3: Looking for password field...")
            self.random_short_delay()

            # Search for input directly (whether enabled or not)
            password_input_selectors = [
                # Very precise search - through Label "Password" and what follows
                "//label[@id=':r9:Label']//following::input[@id=':r9:']",
                "//label[.//span[text()='Password']]/following::input[@type='text'][1]",
                "//div[contains(@class, 'Polaris-FormLayout__Item')]//label[.//span[text()='Password']]/following::input[@type='text'][1]",
                # Search through Labelled container
                "//div[contains(@class, 'Polaris-Labelled')]//label[.//span[text()='Password']]/following::input[@type='text' and contains(@class, 'Polaris-TextField__Input')][1]",
                # Search by attributes
                "//input[@autocomplete='off' and @type='text' and @maxlength='100' and contains(@class, 'Polaris-TextField__Input')]",
                "//input[@data-form-type='other' and @type='text' and contains(@class, 'Polaris-TextField__Input')]"
            ]

            password_input = None
            for i, selector in enumerate(password_input_selectors):
                try:
                    print(f"  Trying selector {i+1}/{len(password_input_selectors)}...")
                    # Use presence only (not clickable) because field might be disabled
                    elements = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_all_elements_located((By.XPATH, selector))
                    )

                    if elements:
                        password_input = elements[0]
                        print(f"✅ Found password field using selector {i+1}")
                        print(f"   Displayed: {password_input.is_displayed()}")
                        print(f"   Enabled: {password_input.is_enabled()}")
                        break

                except Exception as e:
                    print(f"  Selector {i+1} failed: {str(e)[:80]}...")
                    continue

            if not password_input:
                print("❌ Could not find password field at all")
                try:
                    self.driver.save_screenshot("password_field_not_found.png")
                    print("📸 Screenshot saved")
                except:
                    pass
                return False

            # Scroll to element to ensure it's visible
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", password_input)
            self.random_short_delay()

            # Try to enable if disabled
            try:
                if not password_input.is_enabled():
                    print("⚠️ Field is disabled, trying to enable via JavaScript...")
                    self.driver.execute_script("arguments[0].removeAttribute('disabled');", password_input)
                    self.driver.execute_script("arguments[0].removeAttribute('aria-disabled');", password_input)
                    self.driver.execute_script("arguments[0].readOnly = false;", password_input)
                    self.random_short_delay()
                    print("✅ Field enabled via JS")
            except Exception as e:
                print(f"⚠️ Could not enable field: {e}")

            # Try to click on field to ensure focus
            try:
                password_input.click()
                print("✅ Clicked on field")
            except Exception:
                try:
                    self.driver.execute_script("arguments[0].click();", password_input)
                    print("✅ Clicked on field (JS)")
                except Exception as e:
                    print(f"⚠️ Could not click field: {e}")

            self.random_short_delay()

            # Clear old value using JS only (safer)
            try:
                self.driver.execute_script("arguments[0].value = '';", password_input)
                self.driver.execute_script("arguments[0].focus();", password_input)
                print("✅ Cleared password field (JS)")
            except Exception as e:
                print(f"⚠️ Failed to clear field: {e}")

            self.random_short_delay()

            # Enter new password using JS directly
            print(f"✏️ Entering new password: {new_password}")
            try:
                # Use JS to enter value and dispatch Events
                self.driver.execute_script(f"""
                    arguments[0].value = '{new_password}';
                    arguments[0].dispatchEvent(new Event('input', {{ bubbles: true }}));
                    arguments[0].dispatchEvent(new Event('change', {{ bubbles: true }}));
                    arguments[0].focus();
                """, password_input)
                print(f"✅ Password entered via JS: {new_password}")

                # Verify the value
                current_value = password_input.get_attribute('value')
                print(f"   Current value in field: '{current_value}'")

                if current_value != new_password:
                    print(f"⚠️ Value mismatch! Trying again...")
                    self.driver.execute_script(f"arguments[0].value = '{new_password}';", password_input)

            except Exception as e:
                print(f"❌ Failed to enter password: {e}")
                return False

            self.random_short_delay()

            # Step 4: Click Save button
            print("💾 Step 4: Looking for 'Save' button...")
            self.random_short_delay()

            save_button_selectors = [
                "//button[contains(@class, '_ContextualButton') and contains(@class, '_Primary')][@type='submit']",
                "//button[@type='submit' and contains(@class, 'Primary')]",
                "//button[@type='submit']//span[contains(text(), 'Save')]"
            ]

            save_button = None
            for selector in save_button_selectors:
                try:
                    save_button = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    if save_button:
                        print("✅ Found 'Save' button")
                        break
                except Exception:
                    continue

            if not save_button:
                print("❌ Could not find 'Save' button")
                return False

            # Click Save
            try:
                save_button.click()
                print("✅ Clicked 'Save' button")
            except Exception:
                self.driver.execute_script("arguments[0].click();", save_button)
                print("✅ Clicked 'Save' button (JS)")

            self.random_long_delay()

            print("✅ Password changed successfully!")
            print("="*70)
            return True

        except Exception as e:
            print(f"❌ Failed to change password: {str(e)}")
            import traceback
            traceback.print_exc()

            try:
                self.driver.save_screenshot("password_change_error.png")
                print("📸 Screenshot saved: password_change_error.png")
            except Exception:
                pass

            return False

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
            
            unique_name = self.fill_store_name_field()
            if not unique_name:
                raise Exception("Failed to fill store form")
            
            if not self.select_country():
                print("Warning: Failed to select country, continuing anyway...")
            
            if not self.click_create_development_store_button():
                raise Exception("Failed to submit store creation")
            
            if not self.select_account_after_creation():
                raise Exception("Failed to select account after creation")
            
            store_info = self.extract_store_info()
            if not store_info:
                raise Exception("Failed to extract store information")
            
            print("Navigating to admin dashboard...")
            admin_url = store_info['store_url'].rstrip('/') + '/admin'
            self.driver.get(admin_url)
            self.random_long_delay()

            # Change store password to default
            if not self.change_store_password("1234"):
                print("⚠️ Warning: Failed to change store password, continuing anyway...")

            print("="*70)
            print("Store created successfully!")
            print(f"URL: {store_info['store_url']}")
            print(f"ID: {store_info['store_id']}")
            print("="*70)

            store_data = {
                'store_url': store_info['store_url'],
                'store_id': store_info['store_id'],
                'admin_url': admin_url,
                'created_at': store_info.get('created_at')
            }

            return store_data, self.driver
            
        except Exception as e:
            print(f"Store creation failed: {str(e)}")
            
            try:
                if self.driver:
                    self.driver.save_screenshot("store_creation_error.png")
                    print("Screenshot saved: store_creation_error.png")
            except:
                pass
            
            if self.driver:
                self.driver.quit()
                print("Browser closed due to error")
            
            raise