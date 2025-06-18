def scrape_product_info(sku: str, chromedriver_path: str):
    from selenium import webdriver
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException
    import pandas as pd
    import time

    url = f"https://www.homedepot.com.mx/s/{sku}"

    #service = Service(chromedriver_path)
    options = webdriver.ChromeOptions()
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')

    service = Service(ChromeDriverManager(driver_version="120.0.6099.224").install())
    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.get(url)
        print(f"[INFO] Visiting {url}")
        time.sleep(2)

        # Close popup if it appears
        try:
            close_icon = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "dialogStore--icon--highlightOff"))
            )
            close_icon.click()
        except:
            pass

        time.sleep(2)

        # Get product info from that same page
        try:
            name = driver.find_element(By.CLASS_NAME, "product-name").text
        except:
            name = "Not found"

        try:
            desc_elem = driver.find_element(By.CSS_SELECTOR, "p.MuiTypography-root.sc-hsWlPz.juosUc.sc-hrDvXV.iuUlyx.MuiTypography-body1")
            description = desc_elem.text
        except:
            description = "Not found"

        try:
            price_elem = driver.find_element(By.CSS_SELECTOR, "p.product-price")
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
        except:
            price = "Not found"

        try:
            stock_elem = driver.find_element(By.XPATH, "//p[contains(text(), 'disponibles')]")
            stock_digits = ''.join(c for c in stock_elem.text if c.isdigit())
            stock = int(stock_digits) if stock_digits else "Not found"
        except:
            stock = "Not found"

        return pd.DataFrame([{
            "SKU": sku,
            "Name": name,
            "Description": description,
            "Price": price,
            "Stock Available": stock,
            "URL": url
        }])

    finally:
        driver.quit()
