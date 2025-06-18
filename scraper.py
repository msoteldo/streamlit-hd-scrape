from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
import pandas as pd
import concurrent.futures
from threading import Lock
import time
import random

_driver_pool = []  # Pool of drivers for concurrent scraping
_pool_lock = Lock()
MAX_DRIVERS = 2  # Reduced for better reliability

def create_driver():
    """Create a new Chrome driver instance with balanced settings"""
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-plugins')
    # Keep images enabled - some sites need them for proper loading
    options.add_argument('--disable-web-security')
    options.add_argument('--aggressive-cache-discard')
    
    # More conservative page load strategy
    options.page_load_strategy = 'normal'  # Wait for page to load completely
    
    # User agent rotation to avoid detection
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    ]
    options.add_argument(f'--user-agent={random.choice(user_agents)}')
    
    # Performance settings that don't break functionality
    prefs = {
        "profile.default_content_setting_values": {
            "popups": 2,  # Block popups
            "geolocation": 2,  # Block location sharing
            "notifications": 2,  # Block notifications
            "media_stream": 2,  # Block media stream
        }
    }
    options.add_experimental_option("prefs", prefs)
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.binary_location = "/usr/bin/chromium"  # Streamlit Cloud

    service = Service(ChromeDriverManager(driver_version="120.0.6099.224").install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.implicitly_wait(0)  # Disable implicit waits
    driver.set_page_load_timeout(30)  # Increased timeout for reliability
    return driver

def get_driver():
    """Get a driver from the pool or create a new one"""
    with _pool_lock:
        if _driver_pool:
            return _driver_pool.pop()
        else:
            return create_driver()

def return_driver(driver):
    """Return a driver to the pool"""
    try:
        # Clear any cookies/cache to avoid detection
        driver.delete_all_cookies()
        with _pool_lock:
            if len(_driver_pool) < MAX_DRIVERS:
                _driver_pool.append(driver)
            else:
                driver.quit()
    except Exception:
        # If there's an error, just quit the driver
        try:
            driver.quit()
        except:
            pass

def wait_for_page_stable(driver, timeout=10):
    """Wait for page to be stable and ready"""
    try:
        # Wait for document ready state
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        # Small additional wait for dynamic content
        time.sleep(1)
        return True
    except TimeoutException:
        return False

def scrape_product_info_single(sku: str, retry_count=0):
    """Scrape a single product with enhanced reliability"""
    url = f"https://www.homedepot.com.mx/s/{sku}"
    driver = None
    max_retries = 2
    
    try:
        start_time = time.time()
        driver = get_driver()
        
        # Add random delay to avoid rate limiting
        if retry_count == 0:
            time.sleep(random.uniform(0.5, 2.0))
        
        print(f"[INFO] Visiting {url} (attempt {retry_count + 1})")
        
        try:
            driver.get(url)
        except WebDriverException as e:
            if retry_count < max_retries:
                print(f"[WARN] Page load failed for {sku}, retrying...")
                return scrape_product_info_single(sku, retry_count + 1)
            else:
                raise e
        
        # Wait for page to be stable
        if not wait_for_page_stable(driver, timeout=15):
            if retry_count < max_retries:
                print(f"[WARN] Page not stable for {sku}, retrying...")
                return scrape_product_info_single(sku, retry_count + 1)
        
        # Progressive timeout strategy - start with longer waits, reduce as we go
        wait_long = WebDriverWait(driver, 12)
        wait_medium = WebDriverWait(driver, 8)
        wait_short = WebDriverWait(driver, 4)

        # Wait for product name (main indicator page is ready)
        name = None
        try:
            # Try multiple selectors for product name
            selectors = [
                "h1.product-name",
                "h1[data-testid='product-name']",
                ".product-title h1",
                "h1.product-title"
            ]
            
            for selector in selectors:
                try:
                    name_element = wait_long.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    name = name_element.text.strip()
                    if name:
                        break
                except TimeoutException:
                    continue
            
            if not name:
                raise TimeoutException("Product name not found with any selector")
                
        except TimeoutException:
            if retry_count < max_retries:
                print(f"[WARN] Product name not found for {sku}, retrying...")
                return scrape_product_info_single(sku, retry_count + 1)
            else:
                return pd.DataFrame([{
                    "SKU": sku,
                    "Name": "Error",
                    "Description": "Product name not found - page may not have loaded properly",
                    "Price": "",
                    "Stock Available": "",
                    "URL": url
                }])

        # Close popup if it appears (multiple attempts)
        popup_selectors = [
            ".dialogStore--icon--highlightOff",
            "[data-testid='close-button']",
            ".close-button",
            ".popup-close"
        ]
        
        for selector in popup_selectors:
            try:
                close_icon = wait_short.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                close_icon.click()
                time.sleep(0.5)  # Wait for popup to close
                break
            except TimeoutException:
                continue

        # Description with multiple selectors
        description = "Not found"
        description_selectors = [
            "p.MuiTypography-root.sc-hsWlPz.juosUc.sc-hrDvXV.iuUlyx.MuiTypography-body1",
            ".product-description p",
            "[data-testid='product-description']",
            ".product-details p"
        ]
        
        for selector in description_selectors:
            try:
                desc_element = wait_medium.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                description = desc_element.text.strip()
                if description:
                    break
            except TimeoutException:
                continue

        # Price with enhanced extraction
        price = "Not found"
        try:
            price_selectors = [
                "p.product-price",
                ".price",
                "[data-testid='price']",
                ".product-price-container"
            ]
            
            for selector in price_selectors:
                try:
                    price_elem = wait_medium.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    
                    # Enhanced price extraction script
                    js_script = """
                    var element = arguments[0];
                    var mainText = '';
                    var supText = '';
                    var supCount = 0;
                    
                    function extractText(node) {
                        for (var i = 0; i < node.childNodes.length; i++) {
                            var child = node.childNodes[i];
                            if (child.nodeType === Node.TEXT_NODE) {
                                mainText += child.textContent.trim();                
                            } else if (child.nodeType === Node.ELEMENT_NODE && child.tagName === 'SUP') {
                                supCount++;
                                if (supCount === 2) {
                                    supText = child.textContent.trim();
                                }
                            } else if (child.nodeType === Node.ELEMENT_NODE) {
                                extractText(child);
                            }
                        }
                    }
                    
                    extractText(element);
                    return mainText + (supText ? '.' + supText : '');
                    """
                    
                    price_text = driver.execute_script(js_script, price_elem)
                    if price_text:
                        # Clean and convert price
                        price_clean = ''.join(c for c in price_text if c.isdigit() or c == '.')
                        if price_clean:
                            price = round(float(price_clean.replace(',', '')), 2)
                            break
                except (TimeoutException, ValueError, Exception):
                    continue
                    
        except Exception:
            pass

        # Stock with multiple selectors
        stock = "Not found"
        stock_selectors = [
            "//p[contains(text(), 'disponibles')]",
            "//span[contains(text(), 'disponibles')]",
            "//div[contains(text(), 'disponibles')]",
            "[data-testid='stock-info']"
        ]
        
        for selector in stock_selectors:
            try:
                if selector.startswith("//"):
                    stock_elem = wait_medium.until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                else:
                    stock_elem = wait_medium.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                
                stock_digits = ''.join(c for c in stock_elem.text if c.isdigit())
                if stock_digits:
                    stock = int(stock_digits)
                    break
            except TimeoutException:
                continue

        end_time = time.time()
        print(f"[INFO] Successfully scraped {sku} in {end_time - start_time:.2f} seconds")

        return pd.DataFrame([{
            "SKU": sku,
            "Name": name,
            "Description": description,
            "Price": price,
            "Stock Available": stock,
            "URL": url
        }])
    
    except Exception as e:
        print(f"[ERROR] Failed to scrape {sku}: {str(e)}")
        return pd.DataFrame([{
            "SKU": sku,
            "Name": "Error",
            "Description": f"Scraping failed: {str(e)[:100]}",
            "Price": "",
            "Stock Available": "",
            "URL": url
        }])
    
    finally:
        if driver:
            return_driver(driver)

def scrape_product_info_batch(sku_list, max_workers=2):
    """Scrape multiple products with controlled concurrency"""
    if len(sku_list) == 1:
        return scrape_product_info_single(sku_list[0])
    
    results = []
    # Reduce concurrent workers for better reliability
    actual_workers = min(max_workers, len(sku_list), 2)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=actual_workers) as executor:
        future_to_sku = {executor.submit(scrape_product_info_single, sku): sku for sku in sku_list}
        
        for future in concurrent.futures.as_completed(future_to_sku):
            sku = future_to_sku[future]
            try:
                result = future.result(timeout=60)  # 60 second timeout per SKU
                results.append(result)
            except Exception as exc:
                print(f'SKU {sku} generated an exception: {exc}')
                results.append(pd.DataFrame([{
                    "SKU": sku,
                    "Name": "Error",
                    "Description": f"Exception: {str(exc)[:100]}",
                    "Price": "",
                    "Stock Available": "",
                    "URL": f"https://www.homedepot.com.mx/s/{sku}"
                }]))
    
    if results:
        return pd.concat(results, ignore_index=True)
    else:
        return pd.DataFrame()

# Backward compatibility - keep the original function name
def scrape_product_info(sku: str):
    """Original function for single SKU scraping"""
    return scrape_product_info_single(sku)

def cleanup_drivers():
    """Clean up all drivers in the pool"""
    with _pool_lock:
        while _driver_pool:
            driver = _driver_pool.pop()
            try:
                driver.quit()
            except:
                pass