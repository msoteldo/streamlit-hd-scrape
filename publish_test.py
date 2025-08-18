import pandas as pd
import requests
import json

# Cargar categorías
with open("categories.json", "r", encoding="utf-8") as f:
    categories = json.load(f)

# Convertir lista a diccionario para búsqueda rápida por nombre
category_map = {c["name"].lower(): c["id"] for c in categories}


def guess_category(product_name):
    """Adivina category_id a partir del nombre usando coincidencia simple"""
    name_lower = product_name.lower()
    for cname, cid in category_map.items():
        if cname in name_lower:
            return cid
    return "MLA1953"  # Otras categorías por defecto


def build_picture_list(sku):
    """Genera lista de fotos posibles"""
    sku_clean = str(sku).strip()
    base_url = f"https://cdn.homedepot.com.mx/productos/{sku}/{sku}"
    suffixes = ["-d.jpg", "-a1.jpg", "-a2.jpg", "-a3.jpg"]

    pictures = [{"source": f"{base_url}{suffix}"} for suffix in suffixes]

    return pictures

def test_token_region(access_token):
    url_user = "https://api.mercadolibre.com/users/me"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url_user, headers=headers)
    print("User info response:", response.status_code, response.text)
    return response.json()


def publish_or_update_products(csv_file, access_token, skus=None):
    df = pd.read_csv(csv_file, dtype={"SKU": str})

    if skus:
        # Filtrar solo los productos cuyo SKU esté en la lista
        df = df[df["SKU"].isin(skus)]

    # Obtener el seller_id desde /users/me
    user_url = "https://api.mercadolibre.com/users/me"
    headers = {"Authorization": f"Bearer {access_token}"}
    user_resp = requests.get(user_url, headers=headers)
    if user_resp.status_code != 200:
        raise Exception(f"Error obteniendo usuario: {user_resp.text}")
    seller_id = user_resp.json()["id"]

    # Obtener todos los item_ids del seller
    items_url = f"https://api.mercadolibre.com/users/{seller_id}/items/search"
    items_resp = requests.get(items_url, headers=headers)
    if items_resp.status_code != 200:
        raise Exception(f"Error obteniendo items: {items_resp.text}")
    existing_item_ids = set(items_resp.json().get("results", []))

    resultados = []

    for _, row in df.iterrows():
        payload = {
            "title": row["Name"],
            "price": float(row["Price"]),
            "currency_id": "MXN",
            "available_quantity": int(row.get("Stock Available", 0)) if int(row.get("Stock Available", 0)) > 3 else 0,
            "buying_mode": "buy_it_now",
            "condition": "new",
            "listing_type_id": "gold_special",
            "category_id": "MLM3530",  # Fija por ahora
            "description": {
                "plain_text": str(row.get("Description", "")) if str(row.get("Description", "")) != "Not found" else ""
            },
            "pictures": build_picture_list(row["SKU"]),
            "attributes": [
                {"id": "BRAND", "value_name": "TestBrand"},
                {"id": "MODEL", "value_name": "TestModel"},
                {
                    "id": "SELLER_SKU",
                    "name": "SKU",
                    "value_id": None,
                    "value_name": str(row["SKU"]),
                    "value_type": "string"
                }
            ]
        }

        item_id = row["Item_ID"]
        print(item_id)

        print(f"Existing item IDs: {existing_item_ids}")

        if item_id != "" and pd.notna(item_id) and str(item_id) in existing_item_ids:
            # Si existe, actualizamos
            payload.pop("listing_type_id", None)
            payload.pop("description", None)
            url = f"https://api.mercadolibre.com/items/{item_id}"
            response = requests.put(url, headers=headers, data=json.dumps(payload))
            action = "Actualizado"
        else:
            # Si no existe, publicamos nuevo
            url = "https://api.mercadolibre.com/items"
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            action = "Publicado"

        if response.status_code in (200, 201):
            new_item_id = response.json()["id"]
            resultados.append({"SKU": row["SKU"], "item_id": new_item_id, "error": None})
            print("-" * 40)
            print(f"{action} SKU: {row['SKU']} con Item ID: {new_item_id}")
            print("-" * 40)

        else:
            resultados.append({"SKU": row["SKU"], "item_id": None, "error": response.text})
            print(f"Error {action.lower()} SKU {row['SKU']}: {response.text}")

    return resultados


