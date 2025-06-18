import streamlit as st
from scraper import scrape_product_info
import pandas as pd

st.title("Home Depot Product Info by SKU")

# Initialize products_df if not present or cleared
if "products_df" not in st.session_state or st.session_state.get("clear_table", False):
    st.session_state.products_df = pd.DataFrame()
    st.session_state.clear_table = False  # reset the flag

# Clear table button sets the clear flag
if st.button("Clear Table"):
    st.session_state.clear_table = True

sku_input = st.text_area("Enter SKUs (one per line):")

table_placeholder = st.empty()
if not st.session_state.products_df.empty:
    table_placeholder.dataframe(st.session_state.products_df)

if st.button("Get Info for All SKUs"):
    sku_list = [sku.strip() for sku in sku_input.splitlines() if sku.strip()]

    if not sku_list:
        st.warning("Please enter at least one valid SKU.")
    else:
        all_new_data = []

        for i, sku in enumerate(sku_list, start=1):
            with st.spinner(f"Scraping SKU {i} of {len(sku_list)}: {sku}..."):
                try:
                    df = scrape_product_info(sku)
                    st.session_state.products_df = pd.concat([st.session_state.products_df, df], ignore_index=True)
                    table_placeholder.dataframe(st.session_state.products_df)
                except Exception as e:
                    st.error(f"Error scraping SKU {sku}: {e}")

        st.success("All SKUs processed!")
