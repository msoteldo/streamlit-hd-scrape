import streamlit as st
from scraper import scrape_product_info
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

st.title("Home Depot Product Info by SKU")

if "products_df" not in st.session_state or st.session_state.get("clear_table", False):
    st.session_state.products_df = pd.DataFrame()
    st.session_state.clear_table = False

if st.button("Clear Table"):
    st.session_state.clear_table = True

sku_input = st.text_area("Enter SKUs (one per line):")

table_placeholder = st.empty()
if not st.session_state.products_df.empty:
    table_placeholder.dataframe(st.session_state.products_df)

def scrape_wrapper(sku):
    try:
        return scrape_product_info(sku)
    except Exception as e:
        return pd.DataFrame([{
            "SKU": sku,
            "Name": "Error",
            "Description": str(e),
            "Price": None,
            "Stock Available": None,
            "URL": ""
        }])

if st.button("Get Info for All SKUs"):
    sku_list = [sku.strip() for sku in sku_input.splitlines() if sku.strip()]

    if not sku_list:
        st.warning("Please enter at least one valid SKU.")
    else:
        st.session_state.products_df = pd.DataFrame()  # reset before new scrape
        table_placeholder.dataframe(st.session_state.products_df)

        max_workers = min(5, len(sku_list))  # limit concurrency to 5 or less

        with st.spinner("Scraping SKUs concurrently..."):
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(scrape_wrapper, sku): sku for sku in sku_list}

                for i, future in enumerate(as_completed(futures), 1):
                    df = future.result()
                    st.session_state.products_df = pd.concat([st.session_state.products_df, df], ignore_index=True)
                    table_placeholder.dataframe(st.session_state.products_df)
                    st.info(f"Scraped {i} of {len(sku_list)} SKUs")

        st.success("All SKUs processed!")
