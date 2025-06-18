import streamlit as st
from scraper import scrape_product_info_batch, cleanup_drivers
import pandas as pd
import atexit

# Register cleanup function to run when app exits
atexit.register(cleanup_drivers)

st.title("Home Depot Product Info by SKU")

# Initialize products_df if not present or cleared
if "products_df" not in st.session_state or st.session_state.get("clear_table", False):
    st.session_state.products_df = pd.DataFrame()
    st.session_state.clear_table = False  # reset the flag

# Clear table button sets the clear flag
if st.button("Clear Table"):
    st.session_state.clear_table = True

sku_input = st.text_area("Enter SKUs (one per line):")

# Add batch size selector for performance tuning (reduced for reliability)
batch_size = st.selectbox("Batch size (concurrent scraping):", [1, 2, 3], index=1)

# Add retry option
enable_retries = st.checkbox("Enable automatic retries for failed SKUs", value=True)

table_placeholder = st.empty()
if not st.session_state.products_df.empty:
    table_placeholder.dataframe(st.session_state.products_df)

if st.button("Get Info for All SKUs"):
    sku_list = [sku.strip() for sku in sku_input.splitlines() if sku.strip()]

    if not sku_list:
        st.warning("Please enter at least one valid SKU.")
    else:
        # Process in batches for better performance and user feedback
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        total_skus = len(sku_list)
        processed = 0
        
        # Process SKUs in batches
        for i in range(0, len(sku_list), batch_size):
            batch = sku_list[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(sku_list) + batch_size - 1) // batch_size
            
            status_text.text(f"Processing batch {batch_num} of {total_batches} ({len(batch)} SKUs)...")
            
            try:
                # Use batch scraping for concurrent processing
                batch_df = scrape_product_info_batch(batch, max_workers=batch_size)
                
                if not batch_df.empty:
                    st.session_state.products_df = pd.concat([st.session_state.products_df, batch_df], ignore_index=True)
                    table_placeholder.dataframe(st.session_state.products_df)
                
                processed += len(batch)
                progress_bar.progress(processed / total_skus)
                
            except Exception as e:
                st.error(f"Error processing batch {batch_num}: {e}")
                # Continue with next batch instead of stopping entirely
                continue
        
        progress_bar.progress(1.0)
        status_text.text("✅ All SKUs processed!")
        st.success(f"Successfully processed {len(st.session_state.products_df)} products!")

# Add download button for results
if not st.session_state.products_df.empty:
    csv = st.session_state.products_df.to_csv(index=False)
    st.download_button(
        label="Download results as CSV",
        data=csv,
        file_name="home_depot_products.csv",
        mime="text/csv"
    )