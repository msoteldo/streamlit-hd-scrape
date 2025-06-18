from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pandas as pd
import concurrent.futures
from threading import Lock
import time

_driver_pool = []  # Pool of drivers for concurrent scraping
_pool_lock = Lock()
MAX_DRIVERS = 3  # Adjust based on your system resources

def create_driver():
    """Create a new Chrome driver instance with optimized settings"""
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-images')  # Speed boost: don't load images
    options.add_argument('--disable-javascript')  # Speed boost: disable JS if not needed
    options.add_argument('--disable-plugins')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-web-security')
    options.add_argument('--disable-features=VizDisplayCompositor')
    options.add_argument('--aggressive-cache-discard')
    options.add_argument('--memory-pressure-off')
    # Set page load strategy to reduce wait times
    options.page_load_strategy = 'eager'  # Don't wait for all resources
    
    # Additional performance settings
    prefs = {
        "profile.default_content_setting_values": {
            "images": 2,  # Block images
            "plugins": 2,  # Block plugins
            "popups": 2,  # Block popups
            "geolocation": 2,  # Block location sharing
            "notifications": 2,  # Block notifications
            "media_stream": 2,  # Block media stream
        }
    }
    options.add_experimental_option("prefs", prefs)
    options.binary_location = "/usr/bin/chromium"  # Streamlit Cloud

    service = Service(ChromeDriverManager(driver_version="120.0.6099.224").install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.implicitly_wait(0)  # Disable implicit waits
    driver.set_page_load_timeout(15)  # Set page load timeout
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
    with _pool_lock:
        if len(_driver_pool) < MAX_DRIVERS:
            _driver_pool.append(driver)
        else:
            driver.quit()

def scrape_product_info_single(sku: str):
    """Scrape a single product with optimized waits and error handling"""
    url = f"https://www.homedepot.com.mx/s/{sku}"
    driver = get_driver()
    
    try:
        start_time = time.time()
        driver.get(url)
        print(f"[INFO] Visiting {url}")

        # Reduced timeout and more specific waits
        wait_short = WebDriverWait(driver, 3)
        wait_medium = WebDriverWait(driver, 5)

        # Wait for product name (main indicator page is ready)
        try:
            name = wait_medium.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "h1.product-name"))
            ).text
        except TimeoutException:
            return pd.DataFrame([{
                "SKU": sku,
                "Name": "Error",
                "Description": "Page did not load in time",
                "Price": "",
                "Stock Available": "",
                "URL": url
            }])

        # Close popup if it appears (reduced wait time)
        try:
            close_icon = wait_short.until(
                EC.element_to_be_clickable((By.CLASS_NAME, "dialogStore--icon--highlightOff"))
            )
            close_icon.click()
        except TimeoutException:
            pass

        # Gather all elements in parallel with reduced timeouts
        elements = {}
        
        # Description
        try:
            elements['description'] = wait_short.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "p.MuiTypography-root.sc-hsWlPz.juosUc.sc-hrDvXV.iuUlyx.MuiTypography-body1"))
            ).text
        except TimeoutException:
            elements['description'] = "Not found"

        # Price
        try:
            price_elem = wait_short.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "p.product-price"))
            )
            js_script = """
            var element = arguments[0];
            var mainText = '';
            var supText = '';
            var supCount = 0;
            for (var i = 0; i < element.childNodes.length; i++) {
                var node = element.childNodes[i];
                if (node.nodeType === Node.TEXT_NODE) {
                    mainText += node.textContent.trim();                
                } else if (node.nodeType === Node.ELEMENT_NODE && node.tagName === 'SUP') {
                    supCount++;
                    if (supCount === 2) {
                        supText = node.textContent.trim();
                    }
                }
            }
            return mainText + '.' + supText;
            """
            price = round(float(driver.execute_script(js_script, price_elem).replace(',', '')), 2)
        except (TimeoutException, ValueError):
            price = "Not found"

        # Stock
        try:
            stock_elem = wait_short.until(
                EC.presence_of_element_located((By.XPATH, "//p[contains(text(), 'disponibles')]"))
            )
            stock_digits = ''.join(c for c in stock_elem.text if c.isdigit())
            stock = int(stock_digits) if stock_digits else "Not found"
        except TimeoutException:
            stock = "Not found"

        end_time = time.time()
        print(f"[INFO] Scraped {sku} in {end_time - start_time:.2f} seconds")

        return pd.DataFrame([{
            "SKU": sku,
            "Name": name,
            "Description": elements['description'],
            "Price": price,
            "Stock Available": stock,
            "URL": url
        }])
    
    finally:
        return_driver(driver)

def scrape_product_info_batch(sku_list, max_workers=3):
    """Scrape multiple products concurrently"""
    if len(sku_list) == 1:
        return scrape_product_info_single(sku_list[0])
    
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_sku = {executor.submit(scrape_product_info_single, sku): sku for sku in sku_list}
        
        for future in concurrent.futures.as_completed(future_to_sku):
            sku = future_to_sku[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as exc:
                print(f'SKU {sku} generated an exception: {exc}')
                results.append(pd.DataFrame([{
                    "SKU": sku,
                    "Name": "Error",
                    "Description": f"Exception: {str(exc)}",
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
            driver.quit()