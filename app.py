import streamlit as st
from scraper import scrape_product_info
import pandas as pd

st.title("Home Depot Product Info by SKU")

if "products_df" not in st.session_state:
    st.session_state.products_df = pd.DataFrame()

sku = st.text_input("Enter SKU:")

# Placeholder for the data table
table_placeholder = st.empty()

# Show the current table in the placeholder
if not st.session_state.products_df.empty:
    table_placeholder.dataframe(st.session_state.products_df)

if st.button("Get Info"):
    if sku.strip() == "":
        st.warning("Please enter a valid SKU.")
    else:
        with st.spinner("Scraping product info..."):
            new_df = scrape_product_info(sku)

        # Update the cached dataframe by appending new data
        st.session_state.products_df = pd.concat([st.session_state.products_df, new_df], ignore_index=True)

        # Clear the old table (erase placeholder)
        table_placeholder.empty()

        # Show updated table
        table_placeholder.dataframe(st.session_state.products_df)

        st.success("Product info retrieved!")
