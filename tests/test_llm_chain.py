"""
Prueba de la cadena RAG completa con los 3 casos de uso de la rubrica.
Ejecutar desde rag_software_intelligence:
  python tests/test_llm_chain.py

Requiere que el indice ChromaDB ya este construido (test_core_rag.py).
Cada pregunta puede tardar 30-90 segundos.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config.settings import OLLAMA_MODEL, CHROMA_PERSIST_DIR, TOP_K_RESULTS
from core.vector_store import VectorStoreManager
from llm.chain import RAGChain

SEP = "=" * 60

def imprimir_resultado(caso, pregunta, resultado):
    print("\n" + SEP)
    print("  " + caso)
    print("  Pregunta: " + pregunta)
    print(SEP)
    print("  RESPUESTA:")
    print(resultado["answer"])
    print("\n  FUENTES CITADAS:")
    for s in resultado["sources"]:
        print("    [" + s["file"] + "] " + s["preview"][:80])

# Cargar indice existente
print("\n" + SEP)
print("  TEST LLM CHAIN - Casos de Uso de la Rubrica")
print(SEP)

vs = VectorStoreManager(CHROMA_PERSIST_DIR, OLLAMA_MODEL)
if not vs.load_existing():
    print("ERROR: No se encontro el indice ChromaDB.")
    print("Ejecuta primero: python tests/test_core_rag.py")
    sys.exit(1)

chain = RAGChain(vs, model=OLLAMA_MODEL, top_k=TOP_K_RESULTS)

# CASO DE USO 1 — Trazabilidad de campo en codigo fuente
print("\nEjecutando Caso de Uso 1 (puede tardar ~60 seg)...")
r1 = chain.ask(
    "En que archivos de codigo fuente se usa el campo id_cliente "
    "definido en el Diccionario de Datos?"
)
imprimir_resultado("CASO USO 1: Trazabilidad de campo en codigo",
                   "id_cliente en codigo fuente", r1)

# CASO DE USO 2 — Arquitectura Draw.io vs Codigo
print("\nEjecutando Caso de Uso 2 (puede tardar ~60 seg)...")
r2 = chain.ask(
    "Como se relaciona la arquitectura del diagrama con el codigo fuente? "
    "Explica que hace cada capa segun los archivos del repositorio."
)
imprimir_resultado("CASO USO 2: Arquitectura Draw.io vs Codigo",
                   "Relacion arquitectura y codigo", r2)

# CASO DE USO 3 — Impacto de cambios en logica de negocio
print("\nEjecutando Caso de Uso 3 (puede tardar ~60 seg)...")
r3 = chain.ask(
    "Si se cambia el campo estado en la tabla pedidos, "
    "que archivos del codigo fuente se veerian afectados y por que?"
)
imprimir_resultado("CASO USO 3: Impacto de cambios en logica de negocio",
                   "Cambio en campo estado de pedidos", r3)

print("\n" + SEP)
print("  Tests LLM Chain completados")
print("  3 casos de uso de la rubrica ejecutados")
print(SEP)
