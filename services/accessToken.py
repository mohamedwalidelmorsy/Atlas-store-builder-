"""
Shopify Access Token Manager - Using Client Credentials Grant
Creates app in Dev Dashboard, extracts credentials, gets access token via client_credentials
"""

import time
import random
import requests
import re
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


class AccessTokenManager:
    """
    Manages access token retrieval for Shopify stores
    Uses Client Credentials Grant (NOT Authorization Code)
    """
    
    def __init__(self):
        self.driver = None
        self.wait = None
        self.store_domain = None
        self.store_name = None
        
        self.client_id = None
        self.client_secret = None
        self.partner_org_id = None
        self.dev_dashboard_window = None
        self.admin_window = None
    
    def random_delay(self, min_sec=1.5, max_sec=3.5):
        """Random delay"""
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)
    
    def safe_click(self, element, description="element"):
        """Safe click with fallback methods"""
        try:
            element.click()
            print(f"✅ Clicked: {description}")
            return True
        except Exception:
            try:
                self.driver.execute_script("arguments[0].click();", element)
                print(f"✅ JS Clicked: {description}")
                return True
            except Exception as e:
                print(f"❌ Failed to click: {description} - {e}")
                return False
    
    def find_element_safe(self, by, value, timeout=20, description="element"):
        """Safe element finder"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            print(f"✅ Found: {description}")
            return element
        except TimeoutException:
            print(f"❌ Timeout: {description}")
            return None
    
    def navigate_to_dev_dashboard(self):
        """Navigate from Store Admin to Dev Dashboard"""
        try:
            print("\n📂 Navigating to Dev Dashboard...")
            
            # Store current window as admin window
            self.admin_window = self.driver.current_window_handle
            
            # Direct URL to apps development page
            dev_apps_url = f"https://{self.store_domain}/admin/settings/apps/development"
            print(f"🔗 Going to: {dev_apps_url}")
            self.driver.get(dev_apps_url)
            self.random_delay(4, 6)
            
            # Look for "Build apps in Dev Dashboard" button
            dev_button_selectors = [
                "//a[contains(@href, 'dev.shopify.com/dashboard') and contains(@class, 'button-variant-primary')]",
                "//a[contains(@href, 'dev.shopify.com/dashboard')]",
                "//span[contains(text(), 'Build apps in Dev Dashboard')]/ancestor::a"
            ]
            
            dev_button = None
            for selector in dev_button_selectors:
                try:
                    dev_button = self.find_element_safe(By.XPATH, selector, timeout=10, description="Dev Dashboard button")
                    if dev_button:
                        break
                except Exception:
                    continue
            
            if not dev_button:
                print("❌ Dev Dashboard button not found")
                return False
            
            # Extract org ID from URL
            dev_url = dev_button.get_attribute('href')
            match = re.search(r'/dashboard/(\d+)', dev_url)
            if match:
                self.partner_org_id = match.group(1)
                print(f"📌 Partner Org ID: {self.partner_org_id}")
            
            # Click button to open new tab
            if not self.safe_click(dev_button, "Dev Dashboard button"):
                return False
            
            self.random_delay(4, 6)
            
            # Switch to new tab
            windows = self.driver.window_handles
            for window in windows:
                if window != self.admin_window:
                    self.driver.switch_to.window(window)
                    self.dev_dashboard_window = window
                    print("✅ Switched to Dev Dashboard tab")
                    break
            
            self.random_delay(3, 5)
            
            # Verify we're on Dev Dashboard
            current_url = self.driver.current_url
            if 'dev.shopify.com' in current_url:
                print(f"✅ On Dev Dashboard: {current_url}")
                return True
            else:
                print(f"❌ Not on Dev Dashboard: {current_url}")
                return False
            
        except Exception as e:
            print(f"❌ Navigate to Dev Dashboard error: {e}")
            return False
    
    def create_app(self):
        """Create new app in Dev Dashboard"""
        try:
            app_name = f"{self.store_name}-app"
            print(f"\n➕ Creating app: {app_name}")
            
            # Click Create app
            create_selectors = [
                "//a[contains(@href, '/apps/new') and contains(@class, 'button')]",
                "//a[contains(@href, '/apps/new')]"
            ]
            
            create_button = None
            for selector in create_selectors:
                try:
                    create_button = self.find_element_safe(By.XPATH, selector, timeout=10, description="Create app button")
                    if create_button:
                        break
                except Exception:
                    continue
            
            if not create_button:
                print("❌ Create app button not found")
                return False
            
            if not self.safe_click(create_button, "Create app"):
                return False
            
            self.random_delay(4, 6)
            
            # Fill app name
            print(f"✏️ Entering app name: {app_name}")
            name_input = self.find_element_safe(
                By.XPATH,
                "//input[@name='app_form[name]']",
                description="App name input"
            )
            
            if not name_input:
                return False
            
            name_input.clear()
            self.random_delay(0.5, 1)
            name_input.send_keys(app_name)
            self.random_delay(1, 2)
            
            print("✅ App name entered")
            
            # Click Create button to submit the form
            print("🔘 Looking for Create button...")
            create_submit_selectors = [
                "//button[@data-form-target='submit' and @type='submit']",
                "//button[@type='submit' and contains(@class, 'button-variant-primary')]",
                "//button[contains(text(), 'Create')]"
            ]
            
            create_submit_button = None
            for selector in create_submit_selectors:
                try:
                    create_submit_button = self.find_element_safe(By.XPATH, selector, timeout=10, description="Create submit button")
                    if create_submit_button:
                        break
                except Exception:
                    continue
            
            if not create_submit_button:
                print("❌ Create submit button not found")
                return False
            
            if not self.safe_click(create_submit_button, "Create submit button"):
                return False
            
            print("⏳ Waiting for app to be created...")
            self.random_delay(6, 10)
            
            print("✅ App created successfully")
            return True
            
        except Exception as e:
            print(f"❌ Create app error: {e}")
            return False
    
    def configure_scopes(self):
        """Configure API scopes"""
        try:
            scopes = "read_products,write_products"
            print(f"\n🔐 Configuring scopes: {scopes}")
            
            # Verify we're on the app page
            current_url = self.driver.current_url
            print(f"📍 Current URL: {current_url}")
            
            if '/apps/' not in current_url:
                print("⚠️ Not on app page yet, waiting...")
                self.random_delay(3, 5)
            
            # Find scopes textarea
            scopes_textarea = self.find_element_safe(
                By.XPATH,
                "//textarea[@name='version[app_module_data][app_access][app_scopes]']",
                timeout=30,
                description="Scopes textarea"
            )
            
            if not scopes_textarea:
                print("❌ Scopes textarea not found")
                print(f"📍 Page title: {self.driver.title}")
                print(f"📍 Current URL: {self.driver.current_url}")
                
                try:
                    self.driver.save_screenshot(f"scopes_not_found_{self.store_name}.png")
                    print("📸 Screenshot saved")
                except:
                    pass
                
                return False
            
            scopes_textarea.clear()
            self.random_delay(0.5, 1)
            scopes_textarea.send_keys(scopes)
            self.random_delay(1, 2)
            
            print("✅ Scopes configured")
            return True
            
        except Exception as e:
            print(f"❌ Configure scopes error: {e}")
            return False
    
    def release_app(self):
        """Release app version"""
        try:
            version_tag = f"v1.0-{datetime.now().strftime('%Y%m%d')}"
            print(f"\n🚀 Releasing app: {version_tag}")

            # Click Release button - optimized based on provided HTML
            release_button_selectors = [
                "//button[@data-action='modal#toggle' and @data-modal-id-param='release_modal']",
                "//button[@type='button' and contains(@class, 'button-variant-primary')][contains(., 'Release')]",
                "//button[contains(@class, 'button-variant-primary') and contains(@class, 'button-size-medium')][contains(., 'Release')]",
                "//button[text()='Release']",
                "//button[contains(text(), 'Release')]"
            ]

            release_button = None
            for selector in release_button_selectors:
                try:
                    release_button = self.find_element_safe(
                        By.XPATH,
                        selector,
                        timeout=10,
                        description="Release button"
                    )
                    if release_button:
                        print(f"✅ Found Release button")
                        break
                except Exception:
                    continue

            if not release_button:
                print("❌ Release button not found")
                return False

            if not self.safe_click(release_button, "Release button"):
                return False

            self.random_delay(3, 5)

            # Fill version tag - optimized based on provided HTML
            print(f"✏️ Entering version tag: {version_tag}")

            version_input_selectors = [
                "//input[@name='version[version_tag]']",
                "//input[@id='version_version_tag']",
                "//input[@data-form-id-param='version_tag']",
                "//input[@type='text' and @maxlength='100' and contains(@class, 'text-field')]"
            ]

            version_input = None
            for selector in version_input_selectors:
                try:
                    version_input = self.find_element_safe(
                        By.XPATH,
                        selector,
                        timeout=10,
                        description="Version tag input"
                    )
                    if version_input:
                        print(f"✅ Found Version input")
                        break
                except Exception:
                    continue

            if not version_input:
                print("❌ Version input not found")
                return False

            version_input.clear()
            self.random_delay(0.5, 1)
            version_input.send_keys(version_tag)
            self.random_delay(1, 2)
            print(f"✅ Version tag entered: {version_tag}")

            # Submit - optimized based on provided HTML
            submit_button_selectors = [
                "//button[@data-form-target='submit' and @type='submit']",
                "//button[@type='submit' and contains(@class, 'button-variant-primary')][contains(., 'Release')]",
                "//button[@type='submit' and contains(@class, 'button-primary')]",
                "//button[@type='submit']//span[text()='Release']"
            ]

            submit_button = None
            for selector in submit_button_selectors:
                try:
                    submit_button = self.find_element_safe(
                        By.XPATH,
                        selector,
                        timeout=10,
                        description="Submit button"
                    )
                    if submit_button:
                        print(f"✅ Found Submit button")
                        break
                except Exception:
                    continue

            if not submit_button:
                print("❌ Submit button not found")
                return False

            if not self.safe_click(submit_button, "Submit release"):
                return False

            print("⏳ Waiting for release...")
            self.random_delay(6, 10)

            print("✅ App released")
            return True

        except Exception as e:
            print(f"❌ Release error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def navigate_to_settings(self):
        """Navigate to app settings page"""
        try:
            print("\n⚙️ Navigating to Settings...")
            
            settings_link = self.find_element_safe(
                By.XPATH,
                "//a[@aria-label='Settings' and contains(@href, '/settings')]",
                description="Settings link"
            )
            
            if not settings_link:
                print("❌ Settings link not found")
                return False
            
            if not self.safe_click(settings_link, "Settings link"):
                return False
            
            self.random_delay(4, 6)
            print("✅ On Settings page")
            return True
            
        except Exception as e:
            print(f"❌ Navigate to settings error: {e}")
            return False
    
    def extract_credentials(self):
        """Extract Client ID and Secret from Settings page"""
        try:
            print("\n🔑 Extracting credentials...")
            self.random_delay(3, 4)
            
            page_source = self.driver.page_source
            
            # Extract Client ID using regex (32-character hexadecimal)
            print("📋 Getting Client ID...")
            client_id_pattern = r'\b([a-f0-9]{32})\b'
            client_id_matches = re.findall(client_id_pattern, page_source)
            
            if client_id_matches:
                self.client_id = client_id_matches[0]
                print(f"✅ Client ID: {self.client_id}")
            else:
                print("⚠️ Client ID not found in page source")
            
            # Extract Client Secret using regex (starts with shpss_)
            print("📋 Getting Client Secret...")
            secret_pattern = r'(shpss_[a-zA-Z0-9]{30,})'
            secret_matches = re.findall(secret_pattern, page_source)
            
            if secret_matches:
                self.client_secret = secret_matches[0]
                print(f"✅ Client Secret: {self.client_secret[:20]}...")
            else:
                print("⚠️ Client Secret not found in page source")
            
            # Alternative extraction methods if not found
            if not self.client_id or not self.client_secret:
                print("\n🔍 Trying alternative extraction method...")
                
                if not self.client_id:
                    try:
                        copy_id_btn = self.find_element_safe(
                            By.XPATH,
                            "//button[@aria-label='Copy client ID to clipboard']",
                            timeout=5,
                            description="Copy Client ID button"
                        )
                        if copy_id_btn:
                            self.safe_click(copy_id_btn, "Copy Client ID")
                            self.random_delay(2, 3)
                            page_source = self.driver.page_source
                            client_id_matches = re.findall(client_id_pattern, page_source)
                            if client_id_matches:
                                self.client_id = client_id_matches[0]
                                print(f"✅ Client ID (after click): {self.client_id}")
                    except Exception as e:
                        print(f"⚠️ Copy button method failed: {e}")
                
                if not self.client_secret:
                    try:
                        copy_secret_btn = self.find_element_safe(
                            By.XPATH,
                            "//button[@aria-label='Copy client secret to clipboard']",
                            timeout=5,
                            description="Copy Client Secret button"
                        )
                        if copy_secret_btn:
                            self.safe_click(copy_secret_btn, "Copy Client Secret")
                            self.random_delay(2, 3)
                            page_source = self.driver.page_source
                            secret_matches = re.findall(secret_pattern, page_source)
                            if secret_matches:
                                self.client_secret = secret_matches[0]
                                print(f"✅ Client Secret (after click): {self.client_secret[:20]}...")
                    except Exception as e:
                        print(f"⚠️ Copy button method failed: {e}")
            
            # Final element scan if still not found
            if not self.client_id or not self.client_secret:
                print("\n🔍 Searching all elements...")
                
                all_elements = self.driver.find_elements(By.XPATH, "//*")
                for elem in all_elements:
                    try:
                        text = elem.text.strip()
                        value = elem.get_attribute('value')
                        
                        if not self.client_id:
                            if len(text) == 32 and re.match(r'^[a-f0-9]{32}$', text):
                                self.client_id = text
                                print(f"✅ Client ID (element scan): {self.client_id}")
                            elif value and len(value) == 32 and re.match(r'^[a-f0-9]{32}$', value):
                                self.client_id = value
                                print(f"✅ Client ID (value attr): {self.client_id}")
                        
                        if not self.client_secret:
                            if text.startswith('shpss_') and len(text) > 30:
                                self.client_secret = text
                                print(f"✅ Client Secret (element scan): {self.client_secret[:20]}...")
                            elif value and value.startswith('shpss_') and len(value) > 30:
                                self.client_secret = value
                                print(f"✅ Client Secret (value attr): {self.client_secret[:20]}...")
                        
                        if self.client_id and self.client_secret:
                            break
                    except Exception:
                        continue
            
            # Verify
            if self.client_id and self.client_secret:
                print("\n🎉 Credentials extracted successfully!")
                print(f"   Client ID: {self.client_id}")
                print(f"   Client Secret: {self.client_secret[:30]}...")
                return True
            else:
                print("\n❌ Failed to extract credentials")
                print(f"   Client ID found: {bool(self.client_id)}")
                print(f"   Client Secret found: {bool(self.client_secret)}")
                
                try:
                    with open(f"page_source_{self.store_name}.html", 'w', encoding='utf-8') as f:
                        f.write(self.driver.page_source)
                    print(f"💾 Page source saved: page_source_{self.store_name}.html")
                except:
                    pass
                
                try:
                    self.driver.save_screenshot(f"credentials_extraction_failed_{self.store_name}.png")
                    print("📸 Screenshot saved")
                except:
                    pass
                
                return False
            
        except Exception as e:
            print(f"❌ Extract credentials error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def install_app_to_store(self):
        """Install app to store using Custom distribution"""
        try:
            print("\n📦 Installing app to store...")
            
            # Step 1: Click Home
            print("🏠 Clicking Home...")
            home_link = self.find_element_safe(
                By.XPATH,
                "//a[@aria-label='Home' and contains(@href, '/apps/')]",
                description="Home link"
            )
            
            if not home_link:
                print("❌ Home link not found")
                return False
            
            if not self.safe_click(home_link, "Home link"):
                return False
            
            self.random_delay(3, 5)
            
            # Step 2: Click "Select distribution method"
            print("🔗 Clicking 'Select distribution method'...")
            
            current_windows = self.driver.window_handles
            
            distribution_selectors = [
                "//div[contains(@class, 'card')]//p[contains(text(), 'Select distribution method')]/parent::div",
                "//p[text()='Select distribution method']/ancestor::div[contains(@class, 'card')]",
                "//div[contains(@class, 'cursor-pointer')]//p[contains(text(), 'Select distribution method')]"
            ]
            
            distribution_link = None
            for selector in distribution_selectors:
                try:
                    distribution_link = self.find_element_safe(By.XPATH, selector, timeout=10, description="Distribution link")
                    if distribution_link:
                        break
                except Exception:
                    continue
            
            if not distribution_link:
                print("❌ Distribution link not found")
                return False
            
            if not self.safe_click(distribution_link, "Distribution link"):
                return False
            
            print("⏳ Waiting for new tab to open...")
            self.random_delay(5, 8)
            
            new_windows = self.driver.window_handles
            
            if len(new_windows) > len(current_windows):
                for window in new_windows:
                    if window not in current_windows:
                        self.driver.switch_to.window(window)
                        print(f"✅ Switched to distribution tab")
                        print(f"📍 Current URL: {self.driver.current_url}")
                        break
            else:
                print("⚠️ No new tab detected, continuing in same window")
            
            self.random_delay(3, 5)
            
            # Step 3: Check if we need to click user card (old flow) or go directly to radio (new flow)
            print("🔍 Checking page flow...")
            
            # First, check if Custom distribution radio is already visible (new flow - partners.shopify.com)
            custom_radio_check = None
            try:
                elements = self.driver.find_elements(By.XPATH, "//input[@id='PolarisRadioButton2']")
                if elements:
                    custom_radio_check = elements[0]
            except Exception:
                pass

            if not custom_radio_check:
                try:
                    elements = self.driver.find_elements(By.XPATH, "//h6[text()='Custom distribution']")
                    if elements:
                        custom_radio_check = elements[0]
                except:
                    pass
            
            if custom_radio_check:
                print("✅ New flow detected - Custom distribution already visible, skipping user card step")
            else:
                # Old flow - need to click user card first
                print("👤 Old flow detected - Clicking user card...")
                
                user_card_selectors = [
                    "//div[contains(@class, 'user-card')]",
                    "//div[contains(@class, 'user-card__name')]",
                    "//div[contains(text(), '@gmail.com')]"
                ]
                
                user_card = None
                for selector in user_card_selectors:
                    try:
                        user_card = self.find_element_safe(By.XPATH, selector, timeout=10, description="User card")
                        if user_card:
                            break
                    except Exception:
                        continue
                
                if not user_card:
                    print("⚠️ User card not found, trying to continue anyway...")
                else:
                    if not self.safe_click(user_card, "User card"):
                        return False
                    self.random_delay(4, 6)
            
            # Step 4: Select Custom distribution radio button
            print("🔘 Selecting Custom distribution radio...")
            
            custom_radio_selectors = [
                "//input[@id='PolarisRadioButton2']",
                "//input[@name='PolarisRadioButton2']",
                "//input[@type='radio' and @value='custom']",
                "//h6[text()='Custom distribution']/ancestor::div//input[@type='radio']"
            ]
            
            custom_radio = None
            for selector in custom_radio_selectors:
                try:
                    custom_radio = self.find_element_safe(By.XPATH, selector, timeout=10, description="Custom radio")
                    if custom_radio:
                        break
                except Exception:
                    continue
            
            if not custom_radio:
                print("❌ Custom distribution radio not found")
                return False
            
            if not self.safe_click(custom_radio, "Custom distribution radio"):
                return False
            
            self.random_delay(2, 3)
            
            # Step 5: Click "Select" button
            print("✅ Clicking Select button...")
            
            select_button = self.find_element_safe(
                By.XPATH,
                "//button[contains(@class, 'Polaris-Button--primary') and @type='button']//span[text()='Select']",
                description="Select button"
            )
            
            if not select_button:
                print("❌ Select button not found")
                return False
            
            if not self.safe_click(select_button, "Select button"):
                return False
            
            self.random_delay(3, 5)
            
            # Step 6: Click "Select custom distribution" button
            print("✅ Clicking 'Select custom distribution'...")
            
            select_custom_button = self.find_element_safe(
                By.XPATH,
                "//button[contains(@class, 'Polaris-Button--primary')]//span[text()='Select custom distribution']",
                description="Select custom distribution button"
            )
            
            if not select_custom_button:
                print("❌ Select custom distribution button not found")
                return False
            
            if not self.safe_click(select_custom_button, "Select custom distribution"):
                return False
            
            self.random_delay(4, 6)
            
            # Step 7: Enter store domain
            print(f"✏️ Entering store domain: {self.store_domain}")
            
            domain_input_selectors = [
                "//input[@type='text' and contains(@class, 'Polaris-TextField__Input')]",
                "//input[@type='text' and @autocomplete='off']",
                "//input[@placeholder='']"
            ]
            
            domain_input = None
            for selector in domain_input_selectors:
                try:
                    domain_input = self.find_element_safe(By.XPATH, selector, timeout=10, description="Store domain input")
                    if domain_input:
                        break
                except Exception:
                    continue
            
            if not domain_input:
                print("❌ Domain input not found")
                return False
            
            domain_input.clear()
            self.random_delay(0.5, 1)
            domain_input.send_keys(self.store_domain)
            self.random_delay(1, 2)
            
            print("✅ Domain entered")
            
            # Step 8: Click "Generate link" button
            print("🔗 Clicking 'Generate link'...")
            
            generate_button = self.find_element_safe(
                By.XPATH,
                "//button[@type='submit' and contains(@class, 'Polaris-Button--primary')]//span[text()='Generate link']",
                description="Generate link button"
            )
            
            if not generate_button:
                print("❌ Generate link button not found")
                return False
            
            if not self.safe_click(generate_button, "Generate link"):
                return False
            
            self.random_delay(2, 3)
            
            # Step 8.5: Click popup confirmation "Generate link" button
            print("✅ Clicking popup confirmation 'Generate link'...")
            
            popup_generate_button = self.find_element_safe(
                By.XPATH,
                "//button[@type='button' and contains(@class, 'Polaris-Button--primary')]//span[text()='Generate link']",
                description="Popup Generate link button"
            )
            
            if popup_generate_button:
                self.safe_click(popup_generate_button, "Popup Generate link")
            else:
                print("⚠️ Popup button not found, maybe no popup appeared")
            
            self.random_delay(5, 8)
            
            # Step 9: Click "Copy" to copy install link
            print("📋 Clicking Copy button...")
            
            copy_button = self.find_element_safe(
                By.XPATH,
                "//button[@aria-label='Copy to clipboard']//span[text()='Copy']",
                description="Copy button"
            )
            
            if not copy_button:
                print("❌ Copy button not found")
                return False
            
            if not self.safe_click(copy_button, "Copy button"):
                return False
            
            self.random_delay(2, 3)
            
            # Step 10: Get install link from input field
            print("🔍 Getting install link from input field...")
            
            link_input_selectors = [
                "//input[@id='PolarisTextField1']",
                "//input[@disabled and contains(@value, 'https://')]",
                "//input[@disabled and contains(@value, 'oauth')]"
            ]
            
            link_input = None
            for selector in link_input_selectors:
                try:
                    link_input = self.find_element_safe(By.XPATH, selector, timeout=10, description="Link input field")
                    if link_input:
                        break
                except Exception:
                    continue
            
            if not link_input:
                print("❌ Link input field not found")
                try:
                    self.driver.save_screenshot(f"link_input_not_found_{self.store_name}.png")
                except:
                    pass
                return False
            
            install_link = link_input.get_attribute('value')
            
            if install_link and 'https://' in install_link:
                print(f"✅ Install link extracted: {install_link[:70]}...")
            else:
                print(f"❌ Invalid link: {install_link}")
                return False
            
            # Step 11: Open install link in new tab
            print("🌐 Opening install link in new tab...")
            
            self.driver.execute_script("window.open('');")
            self.random_delay(1, 2)
            
            windows = self.driver.window_handles
            install_window = windows[-1]
            self.driver.switch_to.window(install_window)
            
            print(f"🔗 Navigating to install page...")
            self.driver.get(install_link)
            self.random_delay(6, 10)
            
            print("✅ Install page loaded")
            
            # Step 12: Select the CORRECT store by EXACT name
            print(f"🏪 Selecting store: {self.store_name}...")
            self.random_delay(2, 3)

            try:
                # 1. Get the <a> element by EXACT store name
                store_elements = self.driver.find_elements(
                    By.XPATH,
                    f"//a[contains(@class,'_StoreCard')][.//h6[normalize-space()='{self.store_name}']]"
                )

                if not store_elements:
                    raise Exception(f"Store '{self.store_name}' not found in list")

                store_link = store_elements[0]
                print(f"✅ EXACT store found: {self.store_name}")

                # 2. Scroll to element
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});",
                    store_link
                )
                self.random_delay(0.5, 1)

                # 3. Highlight (optional)
                self.driver.execute_script(
                    "arguments[0].style.border='3px solid red';",
                    store_link
                )
                self.random_delay(0.5, 1)

                # 4. Click (JS because Shopify is stubborn)
                self.driver.execute_script("arguments[0].click();", store_link)

                print(f"🖱️ Clicked store: {self.store_name}")

            except Exception as e:
                print(f"❌ Store not found: {self.store_name}")
                print(e)
                try:
                    self.driver.save_screenshot(f"store_not_found_{self.store_name}.png")
                    print("📸 Screenshot saved")
                except:
                    pass
                return False

            self.random_delay(3, 5)
            
            # Step 13: Click "Install" button
            print("📥 Clicking Install button...")
            
            install_button_selectors = [
                "//button[@id='proceed_cta']",
                "//button[contains(@class, 'Polaris-Button--variantPrimary')]//span[text()='Install']",
                "//button[@type='button']//span[text()='Install']"
            ]
            
            install_button = None
            for selector in install_button_selectors:
                try:
                    install_button = self.find_element_safe(By.XPATH, selector, timeout=10, description="Install button")
                    if install_button:
                        break
                except Exception:
                    continue
            
            if not install_button:
                print("❌ Install button not found")
                return False
            
            if not self.safe_click(install_button, "Install button"):
                return False
            
            print("⏳ Waiting for app installation to complete...")
            self.random_delay(8, 12)
            
            print("✅ App installed successfully!")
            
            # Switch back to dev dashboard tab
            print("🔄 Switching back to dev dashboard...")
            self.driver.switch_to.window(self.dev_dashboard_window)
            
            return True
            
        except Exception as e:
            print(f"❌ Install app error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_access_token_from_api(self):
        """
        Get access token using Client Credentials Grant
        
        This is the CORRECT method for Dev Dashboard apps with Custom distribution.
        NO authorization code needed - just Client ID + Client Secret!
        """
        try:
            print("\n🔐 Requesting access token via Client Credentials Grant...")
            print(f"   Client ID: {self.client_id}")
            print(f"   Client Secret: {self.client_secret[:20]}...")
            
            # Shopify OAuth endpoint
            url = f"https://{self.store_domain}/admin/oauth/access_token"
            
            # Headers - IMPORTANT: use application/x-www-form-urlencoded
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            # Client Credentials Grant payload
            payload = {
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret
            }
            
            print(f"\n📡 POST: {url}")
            print(f"📦 Payload: grant_type=client_credentials")
            
            # Make the request
            response = requests.post(url, data=payload, headers=headers)
            
            print(f"\n📊 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                access_token = result.get('access_token')
                
                if access_token:
                    print(f"\n🎉 SUCCESS! Access Token Retrieved!")
                    print(f"🔑 Token: {access_token[:40]}...")
                    print(f"🔐 Scopes: {result.get('scope', 'N/A')}")
                    
                    expires_in = result.get('expires_in')
                    if expires_in:
                        hours = expires_in // 3600
                        print(f"⏰ Expires in: {hours} hours ({expires_in} seconds)")
                    
                    return access_token
                else:
                    print("❌ No access_token in response")
                    print(f"Response: {result}")
                    return None
            else:
                print(f"❌ Token request failed: {response.status_code}")
                print(f"Response: {response.text[:500]}...")
                
                if response.status_code == 400:
                    print("\n💡 Possible reasons for 400 error:")
                    print("   - App not installed on the store yet")
                    print("   - Client ID or Secret is incorrect")
                    print("   - Store domain is incorrect")
                elif response.status_code == 401:
                    print("\n💡 Check that Client ID and Secret are correct")
                
                return None
            
        except Exception as e:
            print(f"❌ Get token error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_token(self, store_url, driver):
        """
        Main method - receives browser session, returns access token
        
        Args:
            store_url: Store URL (e.g., https://mystore.myshopify.com)
            driver: Selenium WebDriver instance from createStore
        
        Returns:
            str: Access token or None if failed
        """
        try:
            print("\n" + "="*70)
            print("SHOPIFY ACCESS TOKEN MANAGER (Client Credentials Grant)")
            print("="*70)
            
            # Setup
            self.driver = driver
            self.wait = WebDriverWait(self.driver, 20)
            
            # Extract store domain
            self.store_domain = store_url.replace('https://', '').replace('http://', '').strip().rstrip('/')
            self.store_name = self.store_domain.split('.')[0]
            
            print(f"📍 Store: {self.store_domain}")
            
            # Step 1: Navigate to Dev Dashboard
            if not self.navigate_to_dev_dashboard():
                raise Exception("Failed to navigate to Dev Dashboard")
            
            # Step 2: Create app
            if not self.create_app():
                raise Exception("Failed to create app")
            
            # Step 3: Configure scopes
            if not self.configure_scopes():
                raise Exception("Failed to configure scopes")
            
            # Step 4: Release app
            if not self.release_app():
                raise Exception("Failed to release app")
            
            # Step 5: Navigate to settings
            if not self.navigate_to_settings():
                raise Exception("Failed to navigate to settings")
            
            # Step 6: Extract credentials
            if not self.extract_credentials():
                raise Exception("Failed to extract credentials")
            
            # Step 7: Install app to store
            if not self.install_app_to_store():
                raise Exception("Failed to install app to store")
            
            # Step 8: Get access token via Client Credentials Grant
            access_token = self.get_access_token_from_api()
            
            if not access_token:
                raise Exception("Failed to get access token")
            
            print("\n" + "="*70)
            print("✅ ACCESS TOKEN RETRIEVED SUCCESSFULLY!")
            print("="*70)
            print(f"Token: {access_token[:40]}...")
            print("="*70 + "\n")
            
            return access_token
            
        except Exception as e:
            print(f"\n❌ Access token retrieval failed: {e}")
            
            try:
                self.driver.save_screenshot(f"access_token_error_{self.store_name}.png")
                print(f"Screenshot saved: access_token_error_{self.store_name}.png")
            except Exception:
                pass
            
            return None