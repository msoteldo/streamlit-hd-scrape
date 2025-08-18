import streamlit as st
from scraper_local import scrape_product_info
from publish_test import publish_or_update_products  # función que acepta lista de SKUs y devuelve [{SKU, item_id},...]
import pandas as pd
import os

st.title("Home Depot Product Info Tracker")

CSV_FILE = "products.csv"

# Cargar CSV o crear DataFrame vacío
if os.path.exists(CSV_FILE):
    products_df = pd.read_csv(CSV_FILE, dtype={"SKU": str})
else:
    products_df = pd.DataFrame(columns=["SKU", "Item_ID", "Name", "Description", "Price", "Stock Available", "URL"], dtype={"SKU": str, "Item_ID": str})

# Inicializar session_state si no existe
if "products_df" not in st.session_state:
    st.session_state.products_df = products_df.copy()

# Asegurar que Item_ID sea string para evitar warnings
st.session_state.products_df["Item_ID"] = st.session_state.products_df["Item_ID"].astype("string")

# Mostrar tabla
st.subheader("Current Product Info")
table_placeholder = st.empty()
table_placeholder.dataframe(st.session_state.products_df)

# Botón limpiar tabla y CSV
if st.button("Clear Table (also clears CSV)"):
    st.session_state.products_df = pd.DataFrame(columns=products_df.columns)
    st.session_state.products_df.to_csv(CSV_FILE, index=False)
    st.rerun()

# --- Actualizar todos los SKUs en CSV ---
if st.button("Update All SKUs in CSV"):
    sku_list = st.session_state.products_df["SKU"].dropna().unique()

    if len(sku_list) == 0:
        st.warning("No SKUs found in CSV.")
    else:
        for i, sku in enumerate(sku_list, start=1):
            with st.spinner(f"Scraping {i} of {len(sku_list)} — SKU: {sku}"):
                try:
                    df = scrape_product_info(sku)

                    # Guardar Item_ID existente
                    existing_item_id = st.session_state.products_df.loc[
                        st.session_state.products_df["SKU"] == sku, "Item_ID"
                    ].values
                    if len(existing_item_id) > 0:
                        df["Item_ID"] = existing_item_id[0]

                    # Reemplazar fila existente y añadir la nueva info
                    st.session_state.products_df = st.session_state.products_df[
                        st.session_state.products_df["SKU"] != sku
                    ]
                    st.session_state.products_df = pd.concat(
                        [st.session_state.products_df, df], ignore_index=True
                    )

                    table_placeholder.dataframe(st.session_state.products_df)

                except Exception as e:
                    st.error(f"Error scraping SKU {sku}: {e}")

        st.session_state.products_df.to_csv(CSV_FILE, index=False)
        st.success("All SKUs updated and saved to CSV!")


# --- Agregar nuevos SKUs manualmente ---
st.subheader("Add New SKUs to CSV")
new_skus = st.text_area("Enter SKUs (one per line):")

if st.button("Add SKUs"):
    sku_list = [sku.strip() for sku in new_skus.splitlines() if sku.strip()]
    if not sku_list:
        st.warning("No SKUs entered.")
    else:
        new_skus_df = pd.DataFrame({"SKU": sku_list})
        existing_skus = set(st.session_state.products_df["SKU"].dropna().unique())
        new_only_df = new_skus_df[~new_skus_df["SKU"].isin(existing_skus)]

        if new_only_df.empty:
            st.info("All entered SKUs already exist.")
        else:
            for i, sku in enumerate(new_only_df["SKU"], start=1):
                with st.spinner(f"Scraping new SKU {i} of {len(new_only_df)} — {sku}"):
                    try:
                        df = scrape_product_info(sku)

                        # No hay Item_ID para nuevos SKUs
                        if "Item_ID" not in df.columns:
                            df["Item_ID"] = ""

                        st.session_state.products_df = pd.concat(
                            [st.session_state.products_df, df],
                            ignore_index=True
                        )
                        table_placeholder.dataframe(st.session_state.products_df)
                    except Exception as e:
                        st.error(f"Error scraping SKU {sku}: {e}")

            st.session_state.products_df.to_csv(CSV_FILE, index=False)
            st.success("New SKUs scraped and added to CSV!")


# --- Actualizar SKUs específicos ---
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
                continue  # saltar SKUs no existentes

            with st.spinner(f"Updating {i} of {len(sku_list)} — SKU: {sku}"):
                try:
                    df = scrape_product_info(sku)

                    # Guardar Item_ID existente
                    existing_item_id = st.session_state.products_df.loc[
                        st.session_state.products_df["SKU"] == sku, "Item_ID"
                    ].values
                    if len(existing_item_id) > 0:
                        df["Item_ID"] = existing_item_id[0]

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


# --- Publicar productos en Mercado Libre ---
st.subheader("Publicar productos en Mercado Libre")
access_token = st.text_input("Access Token de Mercado Libre", type="password")

# Publicar todos los productos
if st.button("Publicar TODOS los productos"):
    if not access_token:
        st.error("Por favor ingresa el Access Token.")
    else:
        sku_list = st.session_state.products_df["SKU"].dropna().unique().tolist()
        sku_list = [str(sku).strip() for sku in sku_list if str(sku).strip()]

        with st.spinner("Publicando todos los productos en Mercado Libre..."):
            try:
                # Convertir columnas a string para evitar warnings al asignar
                st.session_state.products_df["SKU"] = st.session_state.products_df["SKU"].astype(str).str.strip()
                st.session_state.products_df["Item_ID"] = st.session_state.products_df["Item_ID"].astype("string")

                resultados = publish_or_update_products(CSV_FILE, access_token, skus=sku_list)

                errores = [r for r in resultados if r.get("error") and isinstance(r["error"], str) and r["error"].strip()]

                for r in resultados:
                    sku_str = str(r["SKU"]).strip()
                    item_id = str(r["item_id"]).strip()
                    if item_id is None:
                        item_id = ""

                    st.session_state.products_df.loc[
                        st.session_state.products_df["SKU"] == sku_str, "Item_ID"
                    ] = str(item_id)

                st.session_state.products_df.to_csv(CSV_FILE, index=False)

                if errores:
                    for e in errores:
                        st.error(f"Error publicando SKU {e['SKU']}: {e['error']}")
                else:
                    st.success("Productos publicados y CSV actualizado con los Item_ID.")

                table_placeholder.dataframe(st.session_state.products_df)
            except Exception as e:
                st.error(f"Error: {e}")


# Publicar SKUs específicos
st.subheader("Publicar SKUs específicos en Mercado Libre")
skus_to_publish = st.text_area("Ingresa SKUs a publicar (uno por línea):")

if st.button("Publicar estos SKUs"):
    if not access_token:
        st.error("Por favor ingresa el Access Token.")
    else:
        sku_list = [sku.strip() for sku in skus_to_publish.splitlines() if sku.strip()]
        if not sku_list:
            st.warning("No se ingresaron SKUs.")
        else:
            with st.spinner(f"Publicando {len(sku_list)} productos..."):
                try:
                    resultados = publish_or_update_products(CSV_FILE, access_token, skus=sku_list)

                    # Asegurar que columnas sean string para evitar warning
                    st.session_state.products_df["SKU"] = st.session_state.products_df["SKU"].astype(str).str.strip()
                    st.session_state.products_df["Item_ID"] = st.session_state.products_df["Item_ID"].astype("string")

                    errores = []
                    exitos = 0

                    for r in resultados:
                        error_msg = r.get("error")
                        if error_msg and isinstance(error_msg, str) and error_msg.strip():
                            errores.append(f"SKU {r['SKU']}: {error_msg}")
                        else:
                            sku_str = str(r["SKU"]).strip()
                            item_id = r.get("item_id", "")
                            if item_id is None:
                                item_id = ""

                            st.session_state.products_df.loc[
                                st.session_state.products_df["SKU"] == sku_str, "Item_ID"
                            ] = str(item_id)
                            exitos += 1

                    st.session_state.products_df.to_csv(CSV_FILE, index=False)
                    table_placeholder.dataframe(st.session_state.products_df)

                    if exitos > 0:
                        st.success(f"{exitos} productos publicados correctamente y CSV actualizado.")
                    if errores:
                        for err in errores:
                            st.error(err)

                except Exception as e:
                    st.error(f"Error general: {e}")


