"""
Shopify Store Ownership Transfer Service
Automates transferring store ownership to customer via Partners dashboard
"""

import os
import time
import random
from typing import Dict
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from dotenv import load_dotenv

load_dotenv()


class OwnershipTransfer:
    """
    Automates Shopify store ownership transfer through Partners dashboard
    """
    
    def __init__(self, access_token: str, store_url: str):
        """
        Initialize with store credentials
        
        Args:
            access_token: Not used for transfer, but kept for compatibility with app.py
            store_url: Store URL (e.g., store-name.myshopify.com)
        """
        print(f"\n{'='*70}")
        print(f"INITIALIZING OWNERSHIP TRANSFER")
        print(f"{'='*70}")
        
        self.access_token = access_token
        self.store_url = store_url.replace('https://', '').replace('http://', '').split('/')[0]
        self.store_name = self.store_url.split('.')[0]
        
        print(f"Store URL: {self.store_url}")
        print(f"Store Name: {self.store_name}")
        
        # Developer credentials from .env
        self.dev_email = os.getenv('SHOPIFY_DEV_EMAIL')
        self.dev_password = os.getenv('SHOPIFY_DEV_PASSWORD')
        self.partner_id = os.getenv('SHOPIFY_PARTNER_ID', '4498869')
        
        print(f"Dev Email: {self.dev_email}")
        print(f"Partner ID: {self.partner_id}")
        print(f"Password loaded: {'Yes' if self.dev_password else 'No'}")
        print(f"{'='*70}\n")
        
        self.driver = None
        self.wait = None
    
    def wait_random(self, min_sec=0.6, max_sec=2):
        """Wait with random delay"""
        wait_time = random.uniform(min_sec, max_sec)
        time.sleep(wait_time)
    
    def setup_driver(self):
        """Setup Chrome browser"""
        print(f"{'='*70}")
        print(f"SETTING UP CHROME DRIVER")
        print(f"{'='*70}")
        try:
            options = Options()
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            print("Creating Chrome driver...")
            self.driver = webdriver.Chrome(options=options)
            self.driver.maximize_window()
            self.wait = WebDriverWait(self.driver, 30)
            print("✓ Chrome driver setup successful\n")
            return True
        except Exception as e:
            print(f"✗ Failed to setup driver: {str(e)}\n")
            return False
    
    def login_to_partners(self):
        """Login to Shopify Partners dashboard"""
        print(f"{'='*70}")
        print(f"LOGGING IN TO SHOPIFY PARTNERS")
        print(f"{'='*70}")
        try:
            url = f"https://partners.shopify.com/{self.partner_id}/stores"
            print(f"Navigating to: {url}")
            self.driver.get(url)
            self.wait_random(3, 5)
            
            current_url = self.driver.current_url
            
            if 'stores' in current_url:
                print("✓ Already logged in!\n")
                return True
            
            print("Not logged in, proceeding with login...")
            
            # Email
            email_field = self.wait.until(EC.presence_of_element_located((By.NAME, "account[email]")))
            email_field.clear()
            email_field.send_keys(self.dev_email)
            print(f"✓ Email entered: {self.dev_email}")
            
            self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
            self.wait_random(2, 3)
            
            # Password
            password_field = self.wait.until(EC.presence_of_element_located((By.NAME, "account[password]")))
            password_field.clear()
            password_field.send_keys(self.dev_password)
            print("✓ Password entered")
            
            self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
            self.wait_random(5, 8)
            
            final_url = self.driver.current_url
            
            success = 'stores' in final_url or 'partners.shopify.com' in final_url
            if success:
                print("✓ LOGIN SUCCESSFUL\n")
            else:
                print("✗ LOGIN FAILED\n")
            
            return success
        except Exception as e:
            print(f"✗ LOGIN ERROR: {str(e)}\n")
            return False
    
    def search_for_store(self):
        """Search for the store in Partners dashboard"""
        print(f"{'='*70}")
        print(f"SEARCHING FOR STORE")
        print(f"{'='*70}")
        try:
            self.wait_random(3, 5)
            
            search_selectors = [
                "//input[@id='PolarisTextField1']",
                "//input[@placeholder='Filter stores']",
                "//input[contains(@placeholder, 'Filter')]"
            ]
            
            search_input = None
            for selector in search_selectors:
                try:
                    search_input = self.wait.until(EC.presence_of_element_located((By.XPATH, selector)))
                    if search_input.is_displayed():
                        break
                except:
                    continue
            
            if not search_input:
                print("✗ NO SEARCH FIELD FOUND\n")
                return False
            
            search_input.click()
            self.wait_random(0.5, 1)
            search_input.clear()
            search_input.send_keys(self.store_name)
            print(f"✓ Store name entered: {self.store_name}")
            
            self.wait_random(3, 5)
            
            # Verify store appears
            store_selectors = [
                f"//a[contains(text(), '{self.store_name}')]",
                f"//span[contains(text(), '{self.store_name}')]",
                f"//*[contains(text(), '{self.store_name}.myshopify.com')]"
            ]
            
            found = False
            for selector in store_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for elem in elements:
                        if self.store_name.lower() in elem.text.lower():
                            found = True
                            break
                    if found:
                        break
                except:
                    continue
            
            if found:
                print("✓ STORE FOUND IN SEARCH RESULTS\n")
            else:
                print("✗ STORE NOT FOUND\n")
            
            return found
        except Exception as e:
            print(f"✗ SEARCH ERROR: {str(e)}\n")
            return False
    
    def open_actions_menu(self):
        """Open Actions dropdown menu"""
        print(f"{'='*70}")
        print(f"OPENING ACTIONS MENU")
        print(f"{'='*70}")
        try:
            self.wait_random(2, 3)
            
            actions_selectors = [
                "//button[@class='Polaris-Button Polaris-Button--plain' and @type='button']//span[text()='Actions']",
                "//button[contains(@class, 'Polaris-Button--plain')]//span[@class='Polaris-Button__Text' and text()='Actions']",
                "//button[@type='button']//span[text()='Actions']",
                "//span[text()='Actions']/ancestor::button[@type='button']"
            ]
            
            for selector in actions_selectors:
                try:
                    buttons = self.driver.find_elements(By.XPATH, selector)
                    
                    for button in buttons:
                        if button.is_displayed() and button.is_enabled():
                            aria_expanded = button.get_attribute('aria-expanded')
                            
                            if aria_expanded is not None:
                                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                                self.wait_random(1, 2)
                                
                                try:
                                    button.click()
                                except:
                                    self.driver.execute_script("arguments[0].click();", button)
                                
                                self.wait_random(2, 3)
                                
                                new_aria = button.get_attribute('aria-expanded')
                                
                                if new_aria == 'true':
                                    print("✓ DROPDOWN OPENED\n")
                                    return True
                                
                                # Try second click
                                if new_aria == 'false':
                                    self.wait_random(1, 1.5)
                                    self.driver.execute_script("arguments[0].click();", button)
                                    self.wait_random(2, 3)
                                    final_aria = button.get_attribute('aria-expanded')
                                    if final_aria == 'true':
                                        print("✓ OPENED ON 2ND ATTEMPT\n")
                                        return True
                except:
                    continue
            
            print("✗ FAILED TO OPEN ACTIONS MENU\n")
            return False
            
        except Exception as e:
            print(f"✗ CRITICAL ERROR: {str(e)}\n")
            return False
    
    def select_transfer_ownership(self):
        """Select Transfer ownership option from dropdown"""
        print(f"{'='*70}")
        print(f"SELECTING TRANSFER OWNERSHIP")
        print(f"{'='*70}")
        try:
            transfer_selectors = [
                "//span[@class='Polaris-ActionList__Text' and text()='Transfer ownership']",
                "//span[text()='Transfer ownership']",
                "//button[contains(., 'Transfer ownership')]"
            ]
            
            transfer_option = None
            for selector in transfer_selectors:
                try:
                    transfer_option = self.wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    if transfer_option.is_displayed():
                        break
                except:
                    continue
            
            if not transfer_option:
                print("✗ TRANSFER OPTION NOT FOUND\n")
                return False
            
            original_windows = set(self.driver.window_handles)
            
            try:
                transfer_option.click()
            except:
                self.driver.execute_script("arguments[0].click();", transfer_option)
            
            self.wait_random(4, 6)
            
            current_windows = set(self.driver.window_handles)
            
            if len(current_windows) > len(original_windows):
                new_window = list(current_windows - original_windows)[0]
                self.driver.switch_to.window(new_window)
                self.wait_random(2, 3)
            
            print("✓ TRANSFER OWNERSHIP SELECTED\n")
            return True
        except Exception as e:
            print(f"✗ ERROR: {str(e)}\n")
            return False
    
    def open_transfer_form(self):
        """Find and click the account to continue to transfer form"""
        print(f"{'='*70}")
        print(f"OPENING TRANSFER FORM")
        print(f"{'='*70}")
        try:
            self.wait_random(2, 3)
            
            current_url = self.driver.current_url
            
            if 'accounts.shopify.com' not in current_url and 'select' not in current_url:
                print("✗ Not on account selection page\n")
                return False
            
            account_selectors = [
                "//a[contains(@class, 'choose-account-card')]",
                "//a[contains(@class, 'account-picker__item')]",
                "//a[.//div[contains(@class, 'user-card')]]"
            ]
            
            for selector in account_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    
                    for elem in elements:
                        if elem.is_displayed() and elem.is_enabled() and 'Add account' not in elem.text:
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elem)
                            self.wait_random(1, 2)
                            
                            try:
                                elem.click()
                            except:
                                self.driver.execute_script("arguments[0].click();", elem)
                            
                            self.wait_random(3, 5)
                            print("✓ ACCOUNT SELECTED\n")
                            return True
                except:
                    continue
            
            print("✗ NO VALID ACCOUNT FOUND\n")
            return False
        except Exception as e:
            print(f"✗ ERROR: {str(e)}\n")
            return False
    
    def fill_transfer_form(self, customer_email: str, first_name: str, last_name: str):
        """Fill the ownership transfer form"""
        print(f"{'='*70}")
        print(f"FILLING TRANSFER FORM")
        print(f"{'='*70}")
        print(f"Email: {customer_email}")
        print(f"First Name: {first_name}")
        print(f"Last Name: {last_name}")
        
        try:
            self.wait_random(2, 3)
            
            # Email
            try:
                email_field = self.wait.until(EC.presence_of_element_located((By.NAME, "email")))
                if email_field.is_displayed() and email_field.is_enabled():
                    email_field.clear()
                    email_field.send_keys(customer_email)
                    print(f"✓ Email entered")
                    self.wait_random(0.5, 1)
            except Exception as e:
                print(f"✗ Email field error: {str(e)}")
            
            # First Name
            try:
                first_name_field = self.driver.find_element(By.NAME, "firstName")
                if first_name_field.is_displayed() and first_name_field.is_enabled():
                    first_name_field.clear()
                    first_name_field.send_keys(first_name)
                    print(f"✓ First name entered")
                    self.wait_random(0.5, 1)
            except Exception as e:
                print(f"✗ First name field error: {str(e)}")
            
            # Last Name
            try:
                last_name_field = self.driver.find_element(By.NAME, "lastName")
                if last_name_field.is_displayed() and last_name_field.is_enabled():
                    last_name_field.clear()
                    last_name_field.send_keys(last_name)
                    print(f"✓ Last name entered")
                    self.wait_random(0.5, 1)
            except Exception as e:
                print(f"✗ Last name field error: {str(e)}")
            
            # Password
            try:
                password_field = self.driver.find_element(By.NAME, "password")
                if password_field.is_displayed() and password_field.is_enabled():
                    password_field.clear()
                    password_field.send_keys(self.dev_password)
                    print("✓ Password entered")
                    self.wait_random(0.5, 1)
            except Exception as e:
                print(f"✗ Password field error: {str(e)}")
            
            self.wait_random(1, 2)
            print("✓ FORM FILLED\n")
            return True
        except Exception as e:
            print(f"✗ FORM FILL ERROR: {str(e)}\n")
            return False
    
    def submit_transfer(self):
        """Submit the transfer form"""
        print(f"{'='*70}")
        print(f"SUBMITTING TRANSFER")
        print(f"{'='*70}")
        try:
            self.wait_random(1, 2)
            
            submit_selectors = [
                "//button[.//span[text()='Transfer store ownership']]",
                "//button[contains(., 'Transfer store ownership')]",
                "//button[contains(@class, 'Polaris-Button--variantPrimary')]",
                "//button[contains(., 'Transfer')]"
            ]
            
            for selector in submit_selectors:
                try:
                    buttons = self.driver.find_elements(By.XPATH, selector)
                    
                    for button in buttons:
                        if button.is_displayed() and button.is_enabled():
                            button_text = button.text
                            button_class = button.get_attribute('class')
                            
                            if 'Transfer' in button_text or 'variantPrimary' in button_class:
                                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                                self.wait_random(1, 2)
                                
                                try:
                                    button.click()
                                except:
                                    self.driver.execute_script("arguments[0].click();", button)
                                
                                self.wait_random(5, 8)
                                print("✓ TRANSFER SUBMITTED\n")
                                return True
                except:
                    continue
            
            print("✗ NO SUBMIT BUTTON FOUND\n")
            return False
        except Exception as e:
            print(f"✗ SUBMIT ERROR: {str(e)}\n")
            return False
    
    def transfer_to_customer(self, customer_email: str, first_name: str = None, last_name: str = None) -> Dict:
        """
        Main method called by app.py - Fully automated transfer
        
        Args:
            customer_email: Email of the customer to transfer ownership to
            first_name: Customer's first name (optional)
            last_name: Customer's last name (optional)
            
        Returns:
            dict: Transfer result with status
        """
        print(f"\n{'='*70}")
        print(f"STARTING AUTOMATED TRANSFER TO CUSTOMER")
        print(f"{'='*70}")
        print(f"Customer Email: {customer_email}")
        
        try:
            # Set defaults if not provided
            if not first_name:
                email_prefix = customer_email.split('@')[0]
                first_name = ''.join([c for c in email_prefix if not c.isdigit()]) or "Customer"
                print(f"Generated First Name: {first_name}")
            
            if not last_name:
                last_name = "User"
                print(f"Default Last Name: {last_name}")
            
            print(f"{'='*70}\n")
            
            # Execute transfer steps
            steps = [
                ("Setup Browser", self.setup_driver),
                ("Login to Partners", self.login_to_partners),
                ("Search for Store", self.search_for_store),
                ("Open Actions Menu", self.open_actions_menu),
                ("Select Transfer Ownership", self.select_transfer_ownership),
                ("Open Transfer Form", self.open_transfer_form),
                ("Fill Transfer Form", lambda: self.fill_transfer_form(customer_email, first_name, last_name)),
                ("Submit Transfer", self.submit_transfer)
            ]
            
            for idx, (step_name, step_func) in enumerate(steps, 1):
                print(f"▶ Step {idx}/{len(steps)}: {step_name}")
                if not step_func():
                    raise Exception(f"Failed at step: {step_name}")
            
            result = {
                'success': True,
                'store_name': self.store_name,
                'store_url': self.store_url,
                'new_owner': customer_email,
                'transferred_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'note': 'Store ownership transferred successfully via automated process'
            }
            
            print(f"\n{'='*70}")
            print(f"✓✓✓ TRANSFER COMPLETED SUCCESSFULLY ✓✓✓")
            print(f"{'='*70}")
            print(f"Store: {result['store_name']}")
            print(f"New Owner: {result['new_owner']}")
            print(f"Time: {result['transferred_at']}")
            print(f"{'='*70}\n")
            
            return result
            
        except Exception as e:
            error_msg = str(e)
            print(f"\n{'='*70}")
            print(f"✗✗✗ TRANSFER FAILED ✗✗✗")
            print(f"{'='*70}")
            print(f"Error: {error_msg}")
            print(f"{'='*70}\n")
            
            return {
                'success': False,
                'error': error_msg,
                'store_url': self.store_url,
                'new_owner': customer_email
            }
        finally:
            if self.driver:
                print("Closing browser in 3 seconds...")
                time.sleep(3)
                self.driver.quit()
                print("✓ Browser closed\n")


