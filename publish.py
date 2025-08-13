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


def publish_products(csv_file, access_token, skus=None):
    df = pd.read_csv(csv_file, dtype={"SKU": str})

    if skus:
        # Filtrar solo los productos cuyo SKU esté en la lista
        df = df[df["SKU"].isin(skus)]

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
            #"category_id": guess_category(row["Name"]),
            "category_id": "MLM3530",
            "description": {
                "plain_text": str(row.get("Description", "")) if str(row.get("Description", "")) != "Not found" else ""
            },
            "pictures": build_picture_list(row["SKU"]),
              "attributes": [
                {
                "id": "BRAND",
                "value_name": "TestBrand"
                },
                {
                "id": "MODEL",
                "value_name": "TestModel"
                },
                {
                    "id": "SELLER_SKU",
                    "name": "SKU",
                    "value_id": None,
                    "value_name": str(row["SKU"]),
                    "value_type": "string"
                }
            ]
        }

        url = "https://api.mercadolibre.com/items"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

#        print(f"Access Token: {access_token}")
#        # Antes de llamar publish_products, prueba:
#       user_info = test_token_region(access_token)
 #       if user_info.get("site_id") != "MLM":
  #          raise Exception("El token no es para México (MLM). Verifica el access_token.")
  #      else:
 #           print("Token válido para México.")

  #      print(f"Access Token: {access_token}")
 #       print(f"Publicando SKU: {row['SKU']} con payload: {json.dumps(payload, indent=2)}")
        response = requests.post(url, headers=headers, data=json.dumps(payload))

        if response.status_code == 201:
            resultados.append({"SKU": row["SKU"], "item_id": response.json()["id"], "error": None})
            print(f"Publicado SKU: {row['SKU']} con Item ID: {response.json()['id']}")
        else:
            resultados.append({"SKU": row["SKU"], "item_id": None, "error": response.text})

    return resultados


