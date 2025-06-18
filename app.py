import streamlit as st
from scraper import scrape_product_info

st.title("Home Depot Product Info by SKU")

sku = st.text_input("Enter SKU:")
if st.button("Get Info"):
    if sku.strip() == "":
        st.warning("Please enter a valid SKU.")
    else:
        with st.spinner("Scraping product info..."):
            df = scrape_product_info(sku)  # no chromedriver_path arg now
            st.success("Product info retrieved!")
            st.dataframe(df)
