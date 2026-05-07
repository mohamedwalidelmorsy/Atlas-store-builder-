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
from selenium.webdriver.common.action_chains import ActionChains
from dotenv import load_dotenv

load_dotenv()


class OwnershipTransfer:
    """
    Automates Shopify store ownership transfer through Partners dashboard
    """
    
    def __init__(self, access_token: str, store_url: str):
        print(f"\n{'='*70}")
        print(f"INITIALIZING OWNERSHIP TRANSFER")
        print(f"{'='*70}")
        
        self.access_token = access_token
        self.store_url = store_url.replace('https://', '').replace('http://', '').split('/')[0]
        self.store_name = self.store_url.split('.')[0]

        _suffix = '-ts-scout'
        self.base_name = (
            self.store_name[:-len(_suffix)]
            if self.store_name.endswith(_suffix)
            else self.store_name
        )

        print(f"Store URL: {self.store_url}")
        print(f"Store Name: {self.store_name}")
        print(f"Base Name : {self.base_name}")
        
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
        wait_time = random.uniform(min_sec, max_sec)
        time.sleep(wait_time)
    
    def setup_driver(self):
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
            print(" Chrome driver setup successful\n")
            return True
        except Exception as e:
            print(f" Failed to setup driver: {str(e)}\n")
            return False
    
    def login_to_partners(self):
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
                print(" Already logged in!\n")
                return True
            
            print("Not logged in, proceeding with login...")
            
            email_field = self._wait_for_email_field()

            self.driver.execute_script("""
            arguments[0].focus();
            var setter = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype, 'value').set;
            setter.call(arguments[0], arguments[1]);
            arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
            arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
            """, email_field, self.dev_email)
            
            self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
            self.wait_random(2, 3)
            
            password_field = self.wait.until(EC.presence_of_element_located((By.NAME, "account[password]")))
            password_field.clear()
            password_field.send_keys(self.dev_password)
            print(" Password entered")
            
            self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
            self.wait_random(5, 8)
            
            final_url = self.driver.current_url
            
            success = 'stores' in final_url or 'partners.shopify.com' in final_url
            if success:
                print(" LOGIN SUCCESSFUL\n")
            else:
                print(" LOGIN FAILED\n")
            
            return success
        except Exception as e:
            print(f" LOGIN ERROR: {str(e)}\n")
            return False
    
    def search_for_store(self):
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
                print(" NO SEARCH FIELD FOUND\n")
                return False
            
            search_input.click()
            self.wait_random(0.5, 1)
            search_input.clear()
            search_input.send_keys(self.base_name)
            print(f" Search term entered: {self.base_name}")

            self.wait_random(3, 5)

            store_selectors = [
                f"//a[contains(text(), '{self.base_name}')]",
                f"//span[contains(text(), '{self.base_name}')]",
                f"//*[contains(text(), '{self.base_name}')]"
            ]

            found = False
            for selector in store_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for elem in elements:
                        if self.base_name.lower() in elem.text.lower():
                            found = True
                            break
                    if found:
                        break
                except:
                    continue
            
            if found:
                print(" STORE FOUND IN SEARCH RESULTS\n")
            else:
                print(" STORE NOT FOUND\n")
            
            return found
        except Exception as e:
            print(f" SEARCH ERROR: {str(e)}\n")
            return False
    
    def open_actions_menu(self):
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
                                    print(" DROPDOWN OPENED\n")
                                    return True
                                
                                if new_aria == 'false':
                                    self.wait_random(1, 1.5)
                                    self.driver.execute_script("arguments[0].click();", button)
                                    self.wait_random(2, 3)
                                    final_aria = button.get_attribute('aria-expanded')
                                    if final_aria == 'true':
                                        print(" OPENED ON 2ND ATTEMPT\n")
                                        return True
                except:
                    continue
            
            print(" FAILED TO OPEN ACTIONS MENU\n")
            return False
            
        except Exception as e:
            print(f" CRITICAL ERROR: {str(e)}\n")
            return False
    
    def select_transfer_ownership(self):
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
                print(" TRANSFER OPTION NOT FOUND\n")
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
            
            print(" TRANSFER OWNERSHIP SELECTED\n")
            return True
        except Exception as e:
            print(f" ERROR: {str(e)}\n")
            return False
    
    def open_transfer_form(self):
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
                            except Exception:
                                self.driver.execute_script("arguments[0].click();", elem)
                            self.wait_random(3, 5)
                            print("✓ ACCOUNT SELECTED\n")
                            return True
                except Exception:
                    continue

            print("✗ NO VALID ACCOUNT FOUND\n")
            return False
        except Exception as e:
            print(f"✗ ERROR: {str(e)}\n")
            return False

    # ── Diagnostic helpers ──────────────────────────────────────────────────

    def _diag_page_state(self, label: str) -> None:
        sep = "-" * 60
        ts  = time.strftime("%H:%M:%S")
        print(f"\n{sep}")
        print(f"  DIAG [{ts}] {label}")
        print(sep)

        try:
            print(f"  URL        : {self.driver.current_url}")
            print(f"  Title      : {self.driver.title}")
            ready = self.driver.execute_script("return document.readyState")
            print(f"  readyState : {ready}")
        except Exception as e:
            print(f"  URL/title error: {e}")

        try:
            inputs = self.driver.execute_script("""
                return Array.from(document.querySelectorAll('input')).map(function(e) {
                    var r  = e.getBoundingClientRect();
                    var cs = window.getComputedStyle(e);
                    return {
                        type    : e.type,
                        name    : e.name,
                        id      : e.id,
                        disabled: e.disabled,
                        readOnly: e.readOnly,
                        value   : e.value,
                        visible : (r.width > 0 && r.height > 0),
                        display : cs.display,
                        visib   : cs.visibility,
                        opacity : cs.opacity
                    };
                });
            """)
            print(f"  Inputs ({len(inputs)}):")
            for inp in inputs:
                print(f"    {inp}")
        except Exception as e:
            print(f"  inputs error: {e}")

        try:
            logs   = self.driver.get_log('browser')
            errors = [l for l in logs if l.get('level') in ('SEVERE', 'WARNING')]
            if errors:
                print(f"  Console errors ({len(errors)}):")
                for l in errors[-5:]:
                    print(f"    [{l['level']}] {l['message'][:120]}")
            else:
                print("  Console errors: none")
        except Exception:
            pass

        try:
            n = len(self.driver.find_elements(By.TAG_NAME, "iframe"))
            print(f"  iframes    : {n}")
        except Exception:
            pass

        try:
            screenshots_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "screenshots"
            )
            os.makedirs(screenshots_dir, exist_ok=True)
            fname = label.lower().replace(" ", "_").replace("/", "_")
            path  = os.path.join(screenshots_dir,
                                 f"diag_{fname}_{ts.replace(':','')}.png")
            self.driver.save_screenshot(path)
            print(f"  Screenshot : {path}")
        except Exception as e:
            print(f"  screenshot error: {e}")

        print(sep + "\n")

    def _diag_element(self, el, label: str) -> None:
        try:
            attrs = self.driver.execute_script("""
                var el = arguments[0];
                var r  = el.getBoundingClientRect();
                var cs = window.getComputedStyle(el);
                return {
                    tag        : el.tagName,
                    type       : el.type,
                    name       : el.name,
                    id         : el.id,
                    'class'    : el.className,
                    disabled   : el.disabled,
                    readOnly   : el.readOnly,
                    value      : el.value,
                    placeholder: el.placeholder,
                    rect       : {x:Math.round(r.x), y:Math.round(r.y),
                                  w:Math.round(r.width), h:Math.round(r.height)},
                    display    : cs.display,
                    visibility : cs.visibility,
                    opacity    : cs.opacity,
                    ptrEvents  : cs.pointerEvents
                };
            """, el)
            print(f"  [ELEM] {label}: {attrs}")
        except Exception as e:
            print(f"  [ELEM] {label} error: {e}")

    # ── Form filling helpers ────────────────────────────────────────────────

    def _locate_field(self, name: str):
        try:
            return self.driver.find_element(By.CSS_SELECTOR, f"input[name='{name}']")
        except Exception:
            return None

    def _wait_for_email_field(self, timeout=60):
        """
        Wait for a visible email-like input to appear in the DOM.
        Uses JS scan to pierce shadow DOM and find the field by multiple criteria.
        """
        start = time.time()

        while time.time() - start < timeout:
            try:
                email_field = self.driver.execute_script("""
                    // 1. Direct DOM search
                    var el = Array.from(document.querySelectorAll('input')).find(function(e) {
                        var r  = e.getBoundingClientRect();
                        var cs = window.getComputedStyle(e);
                        return (
                            r.width > 50 &&
                            r.height > 20 &&
                            cs.visibility !== 'hidden' &&
                            cs.display !== 'none' &&
                            !e.disabled &&
                            (
                                e.name === 'email' ||
                                e.type === 'email' ||
                                (e.placeholder && e.placeholder.toLowerCase().includes('email')) ||
                                (e.ariaLabel && e.ariaLabel.toLowerCase().includes('email'))
                            )
                        );
                    });
                    if (el) return el;

                    // 2. Shadow DOM search (one level deep)
                    var roots = document.querySelectorAll('*');
                    for (var i = 0; i < roots.length; i++) {
                        if (roots[i].shadowRoot) {
                            var s = roots[i].shadowRoot.querySelector(
                                "input[type='email'], input[name='email']"
                            );
                            if (s) return s;
                        }
                    }
                    return null;
                """)

                if email_field:
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({block:'center'});",
                        email_field
                    )
                    return email_field

            except Exception:
                pass

            print("⏳ Waiting for email field to appear...")
            time.sleep(1)

        raise Exception(f"Could not locate visible email field after {timeout}s")

    def _fill_field(self, el, value: str, label: str) -> bool:
        """
        Fill a single input: scroll → click → clear → send_keys → verify.
        """
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
            time.sleep(0.3)
            el.click()
            time.sleep(0.2)
            el.clear()
            el.send_keys(value)
            time.sleep(0.5)
            actual = el.get_attribute("value") or ""
            if value in actual:
                print(f"✓ {label}: {actual!r}")
                return True
            print(f"✗ {label} mismatch — expected {value!r}, got {actual!r}")
            return False
        except Exception as e:
            print(f"✗ {label} error: {e}")
            return False

    def _fill_email_field(self, el, value: str) -> bool:
        """
        Fill the email field using multiple strategies in order.
        Returns True as soon as one strategy confirms the value is set.
        """
        strategies = [
            # Strategy 1: simple click + send_keys (works in test script)
            lambda: self._strategy_send_keys(el, value),
            # Strategy 2: JS native setter + React events
            lambda: self._strategy_js_native_setter(el, value),
            # Strategy 3: char-by-char with delay
            lambda: self._strategy_char_by_char(el, value),
            # Strategy 4: React fiber hack
            lambda: self._strategy_react_fiber(el, value),
        ]

        for idx, strategy in enumerate(strategies, 1):
            try:
                # Clear first with JS native setter
                self.driver.execute_script("""
                    var s = Object.getOwnPropertyDescriptor(
                        window.HTMLInputElement.prototype, 'value').set;
                    s.call(arguments[0], '');
                    arguments[0].dispatchEvent(new Event('input',  {bubbles: true}));
                    arguments[0].dispatchEvent(new Event('change', {bubbles: true}));
                """, el)
                time.sleep(0.3)

                strategy()
                time.sleep(0.5)

                actual = el.get_attribute("value") or ""
                if value in actual:
                    print(f"✓ email (strategy {idx}): {actual!r}")
                    return True
                else:
                    print(f"  Strategy {idx} got: {actual!r} — trying next...")
            except Exception as e:
                print(f"  Strategy {idx} error: {e} — trying next...")

        return False

    def _strategy_send_keys(self, el, value: str):
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        time.sleep(0.2)
        el.click()
        time.sleep(0.2)
        el.send_keys(value)

    def _strategy_js_native_setter(self, el, value: str):
        self.driver.execute_script("""
            var el = arguments[0], val = arguments[1];
            el.focus();
            var s = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype, 'value').set;
            s.call(el, val);
            el.dispatchEvent(new Event('focus',  {bubbles: true}));
            el.dispatchEvent(new InputEvent('input', {
                bubbles: true, cancelable: true,
                data: val, inputType: 'insertText'
            }));
            el.dispatchEvent(new Event('change', {bubbles: true}));
        """, el, value)

    def _strategy_char_by_char(self, el, value: str):
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        el.click()
        time.sleep(0.2)
        from selenium.webdriver.common.keys import Keys
        el.send_keys(Keys.CONTROL + "a")
        time.sleep(0.1)
        for ch in value:
            el.send_keys(ch)
            time.sleep(0.04)

    def _strategy_react_fiber(self, el, value: str):
        self.driver.execute_script("""
            var el = arguments[0], val = arguments[1];
            var fiberKey = Object.keys(el).find(function(k) {
                return k.startsWith('__reactFiber') || k.startsWith('__reactInternals');
            });
            var s = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype, 'value').set;
            s.call(el, val);
            if (fiberKey) {
                var fiber = el[fiberKey];
                var inst  = fiber && fiber.return;
                while (inst) {
                    var onChange = inst.memoizedProps && inst.memoizedProps.onChange;
                    if (onChange) {
                        el.dispatchEvent(new Event('input', {bubbles: true}));
                        onChange({target: el});
                        break;
                    }
                    inst = inst.return;
                }
            } else {
                el.dispatchEvent(new Event('input',  {bubbles: true}));
                el.dispatchEvent(new Event('change', {bubbles: true}));
            }
        """, el, value)

    # ── Main form filling ───────────────────────────────────────────────────

    def fill_transfer_form(self, customer_email: str, first_name: str, last_name: str) -> bool:
        """Fill the ownership transfer form on admin.shopify.com."""
        print(f"{'='*70}")
        print(f"FILLING TRANSFER FORM")
        print(f"{'='*70}")
        print(f"Email     : {customer_email}")
        print(f"First Name: {first_name}")
        print(f"Last Name : {last_name}")

        # 1. Wait for the browser to land on the final transfer-form URL.
        try:
            self.wait.until(lambda d: (
                'admin.shopify.com' in d.current_url
                and 'transfer_ownership=true' in d.current_url
            ))
            print(f"✓ On transfer form URL: {self.driver.current_url}")
        except Exception:
            print(f"✗ Did not reach admin.shopify.com transfer form "
                  f"(current: {self.driver.current_url})\n")
            return False

        # Snapshot immediately after URL confirmed
        self._diag_page_state("url_confirmed")

        # 2. Wait for the email field using JS scan (handles React lazy render + shadow DOM).
        #    This replaces the old WebDriverWait CSS selector approach which failed because
        #    the email field is NOT present in the DOM at page load — it appears later.
        print("  Waiting for email field (JS scan)...")
        try:
            email_field = self._wait_for_email_field(timeout=60)
            print("✓ Email field located")
        except Exception as e:
            print(f"✗ Email field not found — {e}\n")
            self._diag_page_state("email_field_not_found")
            return False

        self._diag_element(email_field, "email_field_found")

        results = {}

        # 3. Email — try multiple fill strategies until one confirms the value.
        print("  Filling email field...")
        results['email'] = self._fill_email_field(email_field, customer_email)
        if not results['email']:
            print(f"✗ email: all strategies failed")
            self._diag_element(email_field, "email_after_all_strategies")
            self._diag_page_state("email_fill_failed")

        # 4. First Name
        fn_field = self._locate_field("firstName")
        results['firstName'] = (
            self._fill_field(fn_field, first_name, "firstName")
            if fn_field else False
        )
        if not fn_field:
            print("✗ firstName field not found")

        # 5. Last Name
        ln_field = self._locate_field("lastName")
        results['lastName'] = (
            self._fill_field(ln_field, last_name, "lastName")
            if ln_field else False
        )
        if not ln_field:
            print("✗ lastName field not found")

        # 6. Password
        pw_field = self._locate_field("password")
        results['password'] = (
            self._fill_field(pw_field, self.dev_password, "password")
            if pw_field else False
        )
        if not pw_field:
            print("✗ password field not found")

        all_ok = all(results.values())
        if all_ok:
            print("✓ FORM FILLED\n")
        else:
            failed = [k for k, v in results.items() if not v]
            print(f"✗ FORM INCOMPLETE — failed fields: {failed}\n")
        return all_ok

    def submit_transfer(self):
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
                                print(" TRANSFER SUBMITTED\n")
                                return True
                except:
                    continue
            
            print(" NO SUBMIT BUTTON FOUND\n")
            return False
        except Exception as e:
            print(f" SUBMIT ERROR: {str(e)}\n")
            return False
    
    def transfer_to_customer(self, customer_email: str, first_name: str = None, last_name: str = None) -> Dict:
        print(f"\n{'='*70}")
        print(f"STARTING AUTOMATED TRANSFER TO CUSTOMER")
        print(f"{'='*70}")
        print(f"Customer Email: {customer_email}")
        
        try:
            if not first_name:
                email_prefix = customer_email.split('@')[0]
                first_name = ''.join([c for c in email_prefix if not c.isdigit()]) or "Customer"
                print(f"Generated First Name: {first_name}")
            
            if not last_name:
                last_name = "User"
                print(f"Default Last Name: {last_name}")
            
            print(f"{'='*70}\n")
            
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
                print(f" Step {idx}/{len(steps)}: {step_name}")
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
            print(f" TRANSFER COMPLETED SUCCESSFULLY ")
            print(f"{'='*70}")
            print(f"Store: {result['store_name']}")
            print(f"New Owner: {result['new_owner']}")
            print(f"Time: {result['transferred_at']}")
            print(f"{'='*70}\n")
            
            return result
            
        except Exception as e:
            error_msg = str(e)
            print(f"\n{'='*70}")
            print(f" TRANSFER FAILED ")
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
                print(" Browser closed\n")


# ===================================================================
# STANDALONE TEST — run: python services/transferOwner.py
# ===================================================================

def _test():
    import sys
    import json

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, root)

    test_file = os.path.join(root, "data", "test", "test_store_data.json")
    with open(test_file, encoding="utf-8") as f:
        test_data = json.load(f)

    store_info     = test_data["store_info"]
    customer_email = store_info["customer_email"]

    print("=" * 60)
    print("TEST: transfer_to_customer  (REAL BROWSER)")
    print("=" * 60)
    print(f"Store  : {store_info['store_url']}")
    print(f"Email  : {customer_email}")
    print()

    t = OwnershipTransfer(
        access_token=store_info["access_token"],
        store_url=store_info["store_url"]
    )

    if not t.setup_driver():
        print("[RESULT] FAILED — browser setup error")
        return

    url = f"https://partners.shopify.com/{t.partner_id}/stores"
    print(f"Navigating to: {url}")
    t.driver.get(url)

    print()
    print(">>> Browser is open. Please log in to Shopify Partners manually.")
    input(">>> Press Enter once you are on the Stores page... ")
    print()

    email_prefix = customer_email.split('@')[0]
    first_name   = ''.join([c for c in email_prefix if not c.isdigit()]) or "Customer"
    last_name    = "User"

    steps = [
        ("Search for Store",           t.search_for_store),
        ("Open Actions Menu",          t.open_actions_menu),
        ("Select Transfer Ownership",  t.select_transfer_ownership),
        ("Open Transfer Form",         t.open_transfer_form),
        ("Fill Transfer Form",         lambda: t.fill_transfer_form(customer_email, first_name, last_name)),
        ("Submit Transfer",            t.submit_transfer),
    ]

    success = True
    for idx, (name, func) in enumerate(steps, 1):
        print(f"Step {idx}/{len(steps)}: {name}")
        if not func():
            print(f"[RESULT] FAILED at step: {name}")
            success = False
            break

    if success:
        print("[RESULT] Transfer completed successfully!")

    print("\nClosing browser in 3 seconds...")
    time.sleep(3)
    if t.driver:
        t.driver.quit()
    print(" Browser closed")
    print("\n[DONE] transferOwner.py test complete")


if __name__ == "__main__":
    _test()