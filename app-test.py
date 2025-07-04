import streamlit as st
from scraper import scrape_product_info
import pandas as pd
import os

st.title("Home Depot Product Info Tracker")

CSV_FILE = "products.csv"

# Load existing CSV or create a blank DataFrame
if os.path.exists(CSV_FILE):
    products_df = pd.read_csv(CSV_FILE, dtype={"SKU": str})
else:
    products_df = pd.DataFrame(columns=["SKU", "Name", "Description", "Price", "Stock Available", "URL"])

st.session_state.products_df = products_df.copy()

# Clear table button
if st.button("Clear Table (also clears CSV)"):
    st.session_state.products_df = pd.DataFrame(columns=products_df.columns)
    st.session_state.products_df.to_csv(CSV_FILE, index=False)
    st.rerun()

# Show current table
st.subheader("Current Product Info")
st.dataframe(st.session_state.products_df)

# Scrape button
if st.button("Update All SKUs in CSV"):
    sku_list = st.session_state.products_df["SKU"].dropna().unique()

    if len(sku_list) == 0:
        st.warning("No SKUs found in CSV.")
    else:
        for i, sku in enumerate(sku_list, start=1):
            with st.spinner(f"Scraping {i} of {len(sku_list)} — SKU: {sku}"):
                try:
                    df = scrape_product_info(sku)
                    # Remove old SKU row, then append the new
                    st.session_state.products_df = st.session_state.products_df[st.session_state.products_df["SKU"] != sku]
                    st.session_state.products_df = pd.concat([st.session_state.products_df, df], ignore_index=True)
                    st.dataframe(st.session_state.products_df)
                except Exception as e:
                    st.error(f"Error scraping SKU {sku}: {e}")

        # Save updated data to CSV
        st.session_state.products_df.to_csv(CSV_FILE, index=False)
        st.success("All SKUs updated and saved to CSV!")

# Option to add SKUs manually
st.subheader("Add New SKUs to CSV")
new_skus = st.text_area("Enter SKUs (one per line):")

if st.button("Add SKUs"):
    sku_list = [sku.strip() for sku in new_skus.splitlines() if sku.strip()]
    if not sku_list:
        st.warning("No SKUs entered.")
    else:
        new_rows = pd.DataFrame({"SKU": sku_list})
        st.session_state.products_df = pd.concat([st.session_state.products_df, new_rows], ignore_index=True).drop_duplicates(subset="SKU")
        st.session_state.products_df.to_csv(CSV_FILE, index=False)
        st.success("New SKUs added to CSV!")
        st.rerun()
