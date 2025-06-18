# app.py
import streamlit as st
from scraper import scrape_product_info

CHROMEDRIVER_PATH = "C:/Users/migue/Downloads/chromedriver-win64/chromedriver-win64/chromedriver.exe"

st.title("Home Depot Product Info by SKU")

sku = st.text_input("Enter SKU:")
if st.button("Get Info"):
    if sku.strip() == "":
        st.warning("Please enter a valid SKU.")
    else:
        with st.spinner("Scraping product info..."):
            df = scrape_product_info(sku, CHROMEDRIVER_PATH)
            st.success("Product info retrieved!")
            st.dataframe(df)
