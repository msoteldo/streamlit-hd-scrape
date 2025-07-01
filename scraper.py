from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pandas as pd

_driver = None  # module-level private variable for caching driver

def get_driver():
    global _driver
    if _driver is None:
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        #options.binary_location = "/usr/bin/chromium"  # Streamlit Cloud

        service = Service(ChromeDriverManager(driver_version="120.0.6099.224").install())
        _driver = webdriver.Chrome(service=service, options=options)
        _driver.implicitly_wait(0)  # Disable implicit waits for performance
    return _driver

def scrape_product_info(sku: str):
    url = f"https://www.homedepot.com.mx/s/{sku}"
    driver = get_driver()
    driver.get(url)
    print(f"[INFO] Visiting {url}")

    # Wait for product name (main indicator page is ready)
    try:
        name = WebDriverWait(driver, 10).until(
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

    # Close popup if it appears
    try:
        close_icon = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "dialogStore--icon--highlightOff"))
        )
        close_icon.click()
    except TimeoutException:
        pass

    # Description
    try:
        description = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "p.MuiTypography-root.sc-hsWlPz.juosUc.sc-hrDvXV.iuUlyx.MuiTypography-body1"))
        ).text
    except TimeoutException:
        description = "Not found"

    # Price
    try:
        price_elem = WebDriverWait(driver, 5).until(
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
        stock_elem = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//p[contains(text(), 'disponibles')]"))
        )
        stock_digits = ''.join(c for c in stock_elem.text if c.isdigit())
        stock = int(stock_digits) if stock_digits else "Not found"
    except TimeoutException:
        stock = "Not found"

    return pd.DataFrame([{
        "SKU": sku,
        "Name": name,
        "Description": description,
        "Price": price,
        "Stock Available": stock,
        "URL": url
    }])
