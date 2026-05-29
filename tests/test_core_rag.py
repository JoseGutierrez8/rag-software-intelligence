"""
Prueba del Core RAG: pipeline completo de ingesta.
Ejecutar desde rag_software_intelligence:
  python tests/test_core_rag.py

ADVERTENCIA: La primera ejecucion puede tardar 5-15 minutos
porque Ollama genera embeddings para todos los chunks.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.pipeline import IngestionPipeline

SEP = "=" * 55

print("\n" + SEP)
print("  TEST CORE RAG - Pipeline de Ingesta")
print(SEP)
print("  AVISO: La primera vez tarda varios minutos.")
print("         Ollama generara embeddings localmente.")
print(SEP)

pipeline = IngestionPipeline()
total    = pipeline.run(force_rebuild=False)

print("\n" + SEP)
print("  Chunks indexados en ChromaDB:", total)
print(SEP)

if total > 0:
    print("\n  Probando busqueda semantica...")
    vs = pipeline.get_vector_store()

    consultas = [
        "id_cliente campo en tabla clientes",
        "Capa de Presentacion arquitectura",
        "precio stock producto",
    ]
    for q in consultas:
        print("\n  Consulta: " + q)
        results = vs.search(q, k=2)
        for r in results:
            src = r.metadata.get("source", "?")
            print("    [" + src + "] " + r.page_content[:100].replace("\n", " "))

print("\n" + SEP)
print("  Test Core RAG completado")
print(SEP)
