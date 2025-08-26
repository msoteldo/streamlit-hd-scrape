# blob.py
from azure.storage.blob import BlobServiceClient

# Configuración
service_endpoint = "https://blobmercadolibre.blob.core.windows.net"
container_name = "mercadolibre"
sas_token = "sp=racwdlm&st=2025-08-07T19:19:19Z&se=2026-08-08T03:34:19Z&spr=https&sv=2024-11-04&sr=c&sig=38V0zXmvMJT0hsmUFcXDElMq5ZUpiLgcMDBHoXWFsM4%3D"

# Crear cliente del contenedor
blob_service_client = BlobServiceClient(account_url=service_endpoint, credential=sas_token)
container_client = blob_service_client.get_container_client(container_name)

BLOB_PATH = "archivos/products.csv"

def download_products(local_path="products.csv"):
    """Descarga el CSV desde Azure Blob a local."""
    try:
        with open(local_path, "wb") as f:
            data = container_client.download_blob(BLOB_PATH)
            f.write(data.readall())
    except Exception as e:
        print(f"No se pudo descargar {BLOB_PATH}: {e}")

def upload_products(local_path="products.csv"):
    """Sube el CSV local a Azure Blob."""
    with open(local_path, "rb") as f:
        container_client.upload_blob(BLOB_PATH, f, overwrite=True)
