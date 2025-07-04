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

# Store in session
st.session_state.products_df = products_df.copy()

# Table
st.subheader("Current Product Info")
table_placeholder = st.empty()
table_placeholder.dataframe(st.session_state.products_df)

# Clear table
if st.button("Clear Table (also clears CSV)"):
    st.session_state.products_df = pd.DataFrame(columns=products_df.columns)
    st.session_state.products_df.to_csv(CSV_FILE, index=False)
    st.rerun()

# Scrape & update
if st.button("Update All SKUs in CSV"):
    sku_list = st.session_state.products_df["SKU"].dropna().unique()

    if len(sku_list) == 0:
        st.warning("No SKUs found in CSV.")
    else:
        for i, sku in enumerate(sku_list, start=1):
            with st.spinner(f"Scraping {i} of {len(sku_list)} — SKU: {sku}"):
                try:
                    df = scrape_product_info(sku)

                    # Remove existing row for SKU and append the updated one
                    st.session_state.products_df = st.session_state.products_df[
                        st.session_state.products_df["SKU"] != sku
                    ]
                    st.session_state.products_df = pd.concat(
                        [st.session_state.products_df, df], ignore_index=True
                    )

                    # Live update of table
                    table_placeholder.dataframe(st.session_state.products_df)

                except Exception as e:
                    st.error(f"Error scraping SKU {sku}: {e}")

        # Save after all updates
        st.session_state.products_df.to_csv(CSV_FILE, index=False)
        st.success("All SKUs updated and saved to CSV!")

# Add SKUs manually
st.subheader("Add New SKUs to CSV")
new_skus = st.text_area("Enter SKUs (one per line):")

if st.button("Add SKUs"):
    sku_list = [sku.strip() for sku in new_skus.splitlines() if sku.strip()]
    if not sku_list:
        st.warning("No SKUs entered.")
    else:
        new_skus_df = pd.DataFrame({"SKU": sku_list})
        # Filter out SKUs that already exist
        existing_skus = set(st.session_state.products_df["SKU"].dropna().unique())
        new_only_df = new_skus_df[~new_skus_df["SKU"].isin(existing_skus)]

        if new_only_df.empty:
            st.info("All entered SKUs already exist.")
        else:
            for i, sku in enumerate(new_only_df["SKU"], start=1):
                with st.spinner(f"Scraping new SKU {i} of {len(new_only_df)} — {sku}"):
                    try:
                        df = scrape_product_info(sku)
                        st.session_state.products_df = pd.concat(
                            [st.session_state.products_df, df],
                            ignore_index=True
                        )
                        table_placeholder.dataframe(st.session_state.products_df)
                    except Exception as e:
                        st.error(f"Error scraping SKU {sku}: {e}")

            st.session_state.products_df.to_csv(CSV_FILE, index=False)
            st.success("New SKUs scraped and added to CSV!")
            
# Update specific SKUs
st.subheader("Update Specific SKUs")
skus_to_update = st.text_area("Enter SKUs to update (one per line):")

if st.button("Update These SKUs"):
    sku_list = [sku.strip() for sku in skus_to_update.splitlines() if sku.strip()]
    
    if not sku_list:
        st.warning("Please enter at least one SKU.")
    else:
        missing_skus = [sku for sku in sku_list if sku not in st.session_state.products_df["SKU"].values]
        if missing_skus:
            st.warning(f"These SKUs are not in the current table: {', '.join(missing_skus)}")
        
        for i, sku in enumerate(sku_list, start=1):
            if sku not in st.session_state.products_df["SKU"].values:
                continue  # skip ones not already in table

            with st.spinner(f"Updating {i} of {len(sku_list)} — SKU: {sku}"):
                try:
                    df = scrape_product_info(sku)
                    st.session_state.products_df = st.session_state.products_df[
                        st.session_state.products_df["SKU"] != sku
                    ]
                    st.session_state.products_df = pd.concat(
                        [st.session_state.products_df, df], ignore_index=True
                    )
                except Exception as e:
                    st.error(f"Error updating SKU {sku}: {e}")

        st.session_state.products_df.to_csv(CSV_FILE, index=False)
        st.success("Selected SKUs updated!")
        st.rerun()
