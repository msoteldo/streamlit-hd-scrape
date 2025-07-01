import streamlit as st
from scraper import scrape_product_info
import pandas as pd

st.title("Home Depot Product Info by SKU")

# Function to update existing SKUs or append new ones
def update_table(existing_df: pd.DataFrame, new_data: pd.DataFrame) -> pd.DataFrame:
    if existing_df.empty:
        return new_data
    # Remove old rows with the same SKUs as new data
    updated_df = existing_df[~existing_df['SKU'].isin(new_data['SKU'])]
    # Add new data
    updated_df = pd.concat([updated_df, new_data], ignore_index=True)
    return updated_df


# Initialize products_df if not present or cleared
if "products_df" not in st.session_state or st.session_state.get("clear_table", False):
    st.session_state.products_df = pd.DataFrame()
    st.session_state.clear_table = False  # reset the flag

# Clear table button
if st.button("Clear Table"):
    st.session_state.clear_table = True

# Input SKUs
sku_input = st.text_area("Enter SKUs (one per line):")

# Display current table
table_placeholder = st.empty()
if not st.session_state.products_df.empty:
    table_placeholder.dataframe(st.session_state.products_df)

# Get info button
if st.button("Get Info for All SKUs"):
    sku_list = [sku.strip() for sku in sku_input.splitlines() if sku.strip()]

    if not sku_list:
        st.warning("Please enter at least one valid SKU.")
    else:
        for i, sku in enumerate(sku_list, start=1):
            with st.spinner(f"Scraping SKU {i} of {len(sku_list)}: {sku}..."):
                try:
                    df = scrape_product_info(sku)
                    st.session_state.products_df = update_table(st.session_state.products_df, df)
                    table_placeholder.dataframe(st.session_state.products_df)
                except Exception as e:
                    st.error(f"Error scraping SKU {sku}: {e}")

        st.success("All SKUs processed!")
