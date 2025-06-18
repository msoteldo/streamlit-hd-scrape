import streamlit as st
from scraper import scrape_product_info
import pandas as pd

st.title("Home Depot Product Info by SKU")

# Initialize session state DataFrame to store all scraped products
if "products_df" not in st.session_state:
    st.session_state.products_df = pd.DataFrame()

sku = st.text_input("Enter SKU:")
if st.button("Get Info"):
    if sku.strip() == "":
        st.warning("Please enter a valid SKU.")
    else:
        with st.spinner("Scraping product info..."):
            new_df = scrape_product_info(sku)
            # Append new results to existing DataFrame
            st.session_state.products_df = pd.concat([st.session_state.products_df, new_df], ignore_index=True)
            st.success("Product info retrieved!")

# Show the cumulative DataFrame
if not st.session_state.products_df.empty:
    st.dataframe(st.session_state.products_df)
