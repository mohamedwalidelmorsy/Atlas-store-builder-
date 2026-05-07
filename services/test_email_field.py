"""
Standalone diagnostic script — tries 15 different methods to fill the
email input on the Shopify transfer-ownership form and reports which work.

Usage:
    python services/test_email_field.py

Steps:
    1. Opens Chrome and navigates to the transfer form URL.
    2. Waits for you to log in manually and press Enter.
    3. Tries each method in order, clears the field between attempts.
    4. Prints PASS / FAIL per method and a final summary.
"""

import time
import sys

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

EMAIL = "mwaelmorsy18@icloud.com"
URL   = "https://admin.shopify.com/store/weeeee175-ts-scout/settings/account?transfer_ownership=true"

# Selectors tried in order — first match wins
FIELD_SELECTORS = [
    "input[name='email']",
    "input[type='email']",
    "input#P0-0",
    "input[autocomplete='off'][type='email']",
]

# ─────────────────────────────────────────────
#  Core helpers
# ─────────────────────────────────────────────

def get_field(driver, timeout=30):
    """
    Try every selector in FIELD_SELECTORS. If none works via Selenium,
    fall back to a JS full-DOM scan (handles shadow DOM too).
    Raises RuntimeError with diagnostic info on failure.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        # 1. Try each CSS selector
        for sel in FIELD_SELECTORS:
            try:
                els = driver.find_elements(By.CSS_SELECTOR, sel)
                if els:
                    print(f"    [found] selector: {sel!r}")
                    return els[0]
            except Exception:
                pass

        # 2. Try inside any iframes
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for iframe in iframes:
            try:
                driver.switch_to.frame(iframe)
                for sel in FIELD_SELECTORS:
                    els = driver.find_elements(By.CSS_SELECTOR, sel)
                    if els:
                        print(f"    [found in iframe] selector: {sel!r}")
                        return els[0]
                driver.switch_to.default_content()
            except Exception:
                driver.switch_to.default_content()

        # 3. JS scan — pierces shadow DOM one level deep
        el = driver.execute_script(
            """
            // Direct DOM
            var el = document.querySelector("input[type='email']")
                  || document.querySelector("input[name='email']");
            if (el) return el;
            // Shadow DOM (one level)
            var roots = document.querySelectorAll('*');
            for (var i = 0; i < roots.length; i++) {
                if (roots[i].shadowRoot) {
                    var s = roots[i].shadowRoot.querySelector("input[type='email']");
                    if (s) return s;
                }
            }
            return null;
            """
        )
        if el:
            print("    [found] via JS full-DOM scan")
            return el

        time.sleep(0.5)

    # Diagnostic dump
    all_inputs = driver.execute_script(
        "return Array.from(document.querySelectorAll('input')).map(e => "
        "({type:e.type, name:e.name, id:e.id, class:e.className}));"
    )
    print("\n  All <input> elements currently in DOM:")
    for inp in all_inputs:
        print(f"    {inp}")
    raise RuntimeError(
        f"Email field not found after {timeout}s. "
        "Is the transfer-ownership modal actually open?"
    )


def read_value(el):
    return el.get_attribute("value") or ""


def clear_field(driver, el):
    """Reset field to empty using JS native setter so React sees the change."""
    driver.execute_script(
        """
        var s = Object.getOwnPropertyDescriptor(
            window.HTMLInputElement.prototype, 'value').set;
        s.call(arguments[0], '');
        arguments[0].dispatchEvent(new Event('input',  {bubbles: true}));
        arguments[0].dispatchEvent(new Event('change', {bubbles: true}));
        """,
        el,
    )
    time.sleep(0.3)


# ─────────────────────────────────────────────
#  Method 1 — plain send_keys after click
# ─────────────────────────────────────────────
def method_01_send_keys_only(driver, el):
    el.click()
    time.sleep(0.2)
    el.send_keys(EMAIL)


# ─────────────────────────────────────────────
#  Method 2 — clear() then send_keys
# ─────────────────────────────────────────────
def method_02_clear_send_keys(driver, el):
    el.click()
    time.sleep(0.2)
    el.clear()
    el.send_keys(EMAIL)


# ─────────────────────────────────────────────
#  Method 3 — JS value='' then send_keys
# ─────────────────────────────────────────────
def method_03_js_clear_send_keys(driver, el):
    driver.execute_script("arguments[0].value = '';", el)
    time.sleep(0.2)
    el.click()
    el.send_keys(EMAIL)


# ─────────────────────────────────────────────
#  Method 4 — native prototype setter + input/change events
# ─────────────────────────────────────────────
def method_04_native_setter_input_change(driver, el):
    driver.execute_script(
        """
        var s = Object.getOwnPropertyDescriptor(
            window.HTMLInputElement.prototype, 'value').set;
        s.call(arguments[0], arguments[1]);
        arguments[0].dispatchEvent(new Event('input',  {bubbles: true}));
        arguments[0].dispatchEvent(new Event('change', {bubbles: true}));
        """,
        el, EMAIL,
    )


# ─────────────────────────────────────────────
#  Method 5 — native setter + full event chain
# ─────────────────────────────────────────────
def method_05_native_setter_all_events(driver, el):
    driver.execute_script(
        """
        var el = arguments[0], val = arguments[1];
        el.focus();
        var s = Object.getOwnPropertyDescriptor(
            window.HTMLInputElement.prototype, 'value').set;
        s.call(el, val);
        el.dispatchEvent(new Event('focus',  {bubbles: true}));
        el.dispatchEvent(new KeyboardEvent('keydown',  {bubbles: true}));
        el.dispatchEvent(new Event('input',  {bubbles: true}));
        el.dispatchEvent(new KeyboardEvent('keyup',    {bubbles: true}));
        el.dispatchEvent(new Event('change', {bubbles: true}));
        el.dispatchEvent(new Event('blur',   {bubbles: true}));
        """,
        el, EMAIL,
    )


# ─────────────────────────────────────────────
#  Method 6 — ActionChains click + send_keys
# ─────────────────────────────────────────────
def method_06_actionchains_click_keys(driver, el):
    ActionChains(driver).click(el).send_keys(EMAIL).perform()


# ─────────────────────────────────────────────
#  Method 7 — ActionChains triple-click to select all, then type
# ─────────────────────────────────────────────
def method_07_actionchains_triple_click(driver, el):
    ActionChains(driver).double_click(el).click(el).perform()
    time.sleep(0.2)
    el.send_keys(EMAIL)


# ─────────────────────────────────────────────
#  Method 8 — character-by-character send_keys with delay
# ─────────────────────────────────────────────
def method_08_char_by_char(driver, el):
    el.click()
    time.sleep(0.2)
    for ch in EMAIL:
        el.send_keys(ch)
        time.sleep(0.05)


# ─────────────────────────────────────────────
#  Method 9 — JS keyboard events per character + set value
# ─────────────────────────────────────────────
def method_09_js_keyboard_events(driver, el):
    driver.execute_script(
        """
        var el = arguments[0], val = arguments[1];
        el.focus();
        var s = Object.getOwnPropertyDescriptor(
            window.HTMLInputElement.prototype, 'value').set;
        s.call(el, '');
        for (var i = 0; i < val.length; i++) {
            var ch = val[i];
            var code = ch.charCodeAt(0);
            el.dispatchEvent(new KeyboardEvent('keydown',  {key: ch, keyCode: code, bubbles: true}));
            el.dispatchEvent(new KeyboardEvent('keypress', {key: ch, keyCode: code, bubbles: true}));
            s.call(el, val.slice(0, i + 1));
            el.dispatchEvent(new InputEvent('input', {data: ch, bubbles: true}));
            el.dispatchEvent(new KeyboardEvent('keyup', {key: ch, keyCode: code, bubbles: true}));
        }
        el.dispatchEvent(new Event('change', {bubbles: true}));
        """,
        el, EMAIL,
    )


# ─────────────────────────────────────────────
#  Method 10 — setAttribute + events
# ─────────────────────────────────────────────
def method_10_js_set_attribute(driver, el):
    driver.execute_script(
        """
        arguments[0].setAttribute('value', arguments[1]);
        arguments[0].dispatchEvent(new Event('input',  {bubbles: true}));
        arguments[0].dispatchEvent(new Event('change', {bubbles: true}));
        """,
        el, EMAIL,
    )


# ─────────────────────────────────────────────
#  Method 11 — clipboard paste (requires pyperclip)
# ─────────────────────────────────────────────
def method_11_clipboard_paste(driver, el):
    try:
        import pyperclip
        pyperclip.copy(EMAIL)
    except ImportError:
        raise RuntimeError("pyperclip not installed — run: pip install pyperclip")
    el.click()
    time.sleep(0.2)
    el.send_keys(Keys.CONTROL + "a")
    time.sleep(0.1)
    el.send_keys(Keys.CONTROL + "v")


# ─────────────────────────────────────────────
#  Method 12 — Tab into field then send_keys
# ─────────────────────────────────────────────
def method_12_tab_to_field(driver, el):
    # Focus a sibling element first, then Tab to the email field
    driver.execute_script("arguments[0].blur();", el)
    time.sleep(0.2)
    # Find the previous focusable element and tab from it
    driver.execute_script(
        """
        var inputs = document.querySelectorAll('input, button, [tabindex]');
        var idx = Array.prototype.indexOf.call(inputs, arguments[0]);
        if (idx > 0) { inputs[idx - 1].focus(); }
        """,
        el,
    )
    time.sleep(0.2)
    ActionChains(driver).send_keys(Keys.TAB).perform()
    time.sleep(0.3)
    # Now the email field should be focused
    el.send_keys(EMAIL)


# ─────────────────────────────────────────────
#  Method 13 — React fiber onChange hack
# ─────────────────────────────────────────────
def method_13_react_fiber_hack(driver, el):
    driver.execute_script(
        """
        var el = arguments[0], val = arguments[1];
        var fiber = el._reactFiber
            || el.__reactFiber
            || el[Object.keys(el).find(k => k.startsWith('__reactFiber'))];
        if (!fiber) {
            // Try internal instance
            fiber = el._reactInternals
                || el.__reactInternals
                || el[Object.keys(el).find(k => k.startsWith('__reactInternals'))];
        }
        if (fiber) {
            var inst = fiber.return;
            while (inst) {
                var onChange = inst.memoizedProps && inst.memoizedProps.onChange;
                if (onChange) {
                    var nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                        window.HTMLInputElement.prototype, 'value').set;
                    nativeInputValueSetter.call(el, val);
                    el.dispatchEvent(new Event('input', {bubbles: true}));
                    onChange({target: el});
                    break;
                }
                inst = inst.return;
            }
        } else {
            // Fallback: native setter
            var s = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype, 'value').set;
            s.call(el, val);
            el.dispatchEvent(new Event('input', {bubbles: true}));
            el.dispatchEvent(new Event('change', {bubbles: true}));
        }
        """,
        el, EMAIL,
    )


# ─────────────────────────────────────────────
#  Method 14 — JS focus + value + InputEvent with data
# ─────────────────────────────────────────────
def method_14_js_focus_value_input_event(driver, el):
    driver.execute_script(
        """
        var el = arguments[0], val = arguments[1];
        el.focus();
        var s = Object.getOwnPropertyDescriptor(
            window.HTMLInputElement.prototype, 'value').set;
        s.call(el, val);
        el.dispatchEvent(new InputEvent('input', {
            bubbles: true,
            cancelable: true,
            data: val,
            inputType: 'insertText'
        }));
        el.dispatchEvent(new Event('change', {bubbles: true}));
        """,
        el, EMAIL,
    )


# ─────────────────────────────────────────────
#  Method 15 — Ctrl+A on element + type to overwrite
# ─────────────────────────────────────────────
def method_15_select_all_type(driver, el):
    el.click()
    time.sleep(0.2)
    el.send_keys(Keys.CONTROL + "a")
    time.sleep(0.1)
    el.send_keys(EMAIL)


# ─────────────────────────────────────────────
#  Method registry
# ─────────────────────────────────────────────
METHODS = [
    ("01_send_keys_only",            method_01_send_keys_only),
    ("02_clear_send_keys",           method_02_clear_send_keys),
    ("03_js_clear_send_keys",        method_03_js_clear_send_keys),
    ("04_native_setter_input_change",method_04_native_setter_input_change),
    ("05_native_setter_all_events",  method_05_native_setter_all_events),
    ("06_actionchains_click_keys",   method_06_actionchains_click_keys),
    ("07_actionchains_triple_click", method_07_actionchains_triple_click),
    ("08_char_by_char",              method_08_char_by_char),
    ("09_js_keyboard_events",        method_09_js_keyboard_events),
    ("10_js_set_attribute",          method_10_js_set_attribute),
    ("11_clipboard_paste",           method_11_clipboard_paste),
    ("12_tab_to_field",              method_12_tab_to_field),
    ("13_react_fiber_hack",          method_13_react_fiber_hack),
    ("14_js_focus_value_input_event",method_14_js_focus_value_input_event),
    ("15_select_all_type",           method_15_select_all_type),
]


# ─────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  Email Field Diagnostic — Shopify Transfer Form")
    print("=" * 60)

    driver = webdriver.Chrome()
    driver.maximize_window()
    driver.get(URL)

    print(f"\nOpened: {URL}")
    print("\nPlease log in to Shopify and make sure the transfer")
    print("ownership form is visible on screen, then press Enter.")
    input()

    try:
        el = get_field(driver)
    except Exception:
        print("ERROR: Could not find input[name='email'] on the page.")
        print("Make sure the transfer form is open (modal visible).")
        driver.quit()
        sys.exit(1)

    print(f"\nFound email field. Running {len(METHODS)} methods...\n")
    print("-" * 60)

    results = []
    for name, fn in METHODS:
        # Clear between attempts
        try:
            clear_field(driver, el)
        except Exception:
            pass
        time.sleep(0.4)

        # Re-locate element in case of stale reference
        try:
            el = get_field(driver)
        except Exception:
            results.append((name, False, "stale element — could not re-locate"))
            continue

        try:
            fn(driver, el)
            time.sleep(0.5)
            val = read_value(el)
            ok  = EMAIL in val
        except Exception as exc:
            val = str(exc)[:80]
            ok  = False

        status = "PASS" if ok else "FAIL"
        print(f"  [{status}]  {name}")
        if ok:
            print(f"         value = {val!r}")
        else:
            print(f"         got   = {val!r}")
        results.append((name, ok, val))

    # ── Summary ──────────────────────────────
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    passed = [n for n, ok, _ in results if ok]
    failed = [n for n, ok, _ in results if not ok]

    for name, ok, val in results:
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}]  {name}")

    print(f"\nPassed: {len(passed)}/{len(results)}")
    if passed:
        print(f"\nFirst working method: {passed[0]}")
        print("Use this technique in fill_transfer_form() in transferOwner.py")

    input("\nPress Enter to close the browser...")
    driver.quit()


if __name__ == "__main__":
    main()
