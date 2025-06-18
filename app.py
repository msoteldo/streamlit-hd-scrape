import streamlit as st
from scraper import scrape_product_info
import pandas as pd

st.title("Home Depot Product Info by SKU")

if "products_df" not in st.session_state:
    st.session_state.products_df = pd.DataFrame()

# Multiline text area for multiple SKUs, one per line
sku_input = st.text_area("Enter SKUs (one per line):")

table_placeholder = st.empty()
if not st.session_state.products_df.empty:
    table_placeholder.dataframe(st.session_state.products_df)

if st.button("Get Info for All SKUs"):
    # Clean and split the input into a list of SKUs
    sku_list = [sku.strip() for sku in sku_input.splitlines() if sku.strip()]
    
    if not sku_list:
        st.warning("Please enter at least one valid SKU.")
    else:
        with st.spinner(f"Scraping info for {len(sku_list)} SKUs..."):
            all_new_data = []
            for sku in sku_list:
                try:
                    df = scrape_product_info(sku)
                    all_new_data.append(df)
                except Exception as e:
                    st.error(f"Error scraping SKU {sku}: {e}")

            if all_new_data:
                new_df = pd.concat(all_new_data, ignore_index=True)
                st.session_state.products_df = pd.concat([st.session_state.products_df, new_df], ignore_index=True)

        table_placeholder.empty()
        table_placeholder.dataframe(st.session_state.products_df)
        st.success("All SKUs processed!")
