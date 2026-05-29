"""
Diagnostica que chunks se recuperan para distintas consultas.
Ejecutar desde rag_software_intelligence:
  python diagnostico_busqueda.py
"""
import sys, os
sys.path.insert(0, ".")

from config.settings import CHROMA_PERSIST_DIR, OLLAMA_MODEL
from core.vector_store import VectorStoreManager

vs = VectorStoreManager(CHROMA_PERSIST_DIR, OLLAMA_MODEL)
if not vs.load_existing():
    print("ERROR: No hay indice. Indexa primero desde Streamlit.")
    sys.exit(1)

print("\nTotal en indice:", vs.count())
SEP = "-" * 60

consultas = [
    "registrar_entrada inventario_service",
    "def registrar_entrada id_producto id_bodega cantidad",
    "stock_minimo producto alerta",
    "RolUsuario administrador bodeguero permisos",
    "EstadoPedido borrador enviado confirmado recibido",
]

for q in consultas:
    print("\n" + SEP)
    print("CONSULTA:", q)
    print(SEP)
    results = vs.search(q, k=3)
    for r in results:
        src = r.metadata.get("source", "?")
        loader = r.metadata.get("loader", "?")
        print("  [" + loader + "] " + src)
        print("  " + r.page_content[:150].replace("\n", " "))
        print()
