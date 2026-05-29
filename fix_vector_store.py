"""
Corrige el error de PermissionError en vector_store.py (Windows).
Ejecutar desde rag_software_intelligence:
  python fix_vector_store.py
"""
import os

CONTENT = """\
import os
import gc
from typing import List, Optional
from langchain.schema import Document
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings


class VectorStoreManager:
    \"\"\"
    Gestiona la base de datos vectorial ChromaDB con embeddings de Ollama.
    \"\"\"

    COLLECTION = "rag_software_intelligence"

    def __init__(self, persist_dir: str, model: str = "llama3.2"):
        self.persist_dir = persist_dir
        self.embeddings  = OllamaEmbeddings(model=model)
        self.store: Optional[Chroma] = None

    def build(self, documents: List[Document]) -> None:
        if not documents:
            raise ValueError("No hay documentos para indexar.")

        print("  [VectorStore] Construyendo indice con", len(documents), "chunks...")
        print("  [VectorStore] (esto puede tardar varios minutos la primera vez)")

        # Liberar referencia anterior antes de intentar borrar
        if self.store is not None:
            del self.store
            self.store = None
            gc.collect()

        # Intentar limpiar directorio anterior
        if os.path.exists(self.persist_dir):
            self._safe_rmtree(self.persist_dir)

        # Crear nuevo indice en lotes
        batch_size = 50
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            if i == 0:
                self.store = Chroma.from_documents(
                    documents=batch,
                    embedding=self.embeddings,
                    persist_directory=self.persist_dir,
                    collection_name=self.COLLECTION,
                )
            else:
                self.store.add_documents(batch)
            pct = min(100, int((i + len(batch)) / len(documents) * 100))
            print("    Progreso: " + str(pct) + "%  ("
                  + str(i + len(batch)) + "/" + str(len(documents)) + " chunks)")

        print("  [VectorStore] Indice guardado en", self.persist_dir)

    def load_existing(self) -> bool:
        if not os.path.exists(self.persist_dir):
            return False
        try:
            self.store = Chroma(
                persist_directory=self.persist_dir,
                embedding_function=self.embeddings,
                collection_name=self.COLLECTION,
            )
            count = self.store._collection.count()
            print("  [VectorStore] Indice cargado:", count, "chunks")
            return count > 0
        except Exception as e:
            print("  [VectorStore] Indice no utilizable:", str(e))
            return False

    def search(self, query: str, k: int = 5) -> List[Document]:
        if self.store is None:
            raise RuntimeError("VectorStore no inicializado.")
        return self.store.similarity_search(query, k=k)

    def count(self) -> int:
        if self.store is None:
            return 0
        return self.store._collection.count()

    @staticmethod
    def _safe_rmtree(path: str) -> None:
        \"\"\"Borra un directorio en Windows manejando archivos bloqueados.\"\"\"
        import shutil, time
        for attempt in range(3):
            try:
                shutil.rmtree(path)
                return
            except PermissionError:
                if attempt < 2:
                    time.sleep(1)
                else:
                    # Ultimo intento: borrar archivo por archivo
                    for root, dirs, files in os.walk(path, topdown=False):
                        for fname in files:
                            try:
                                os.remove(os.path.join(root, fname))
                            except Exception:
                                pass
                        for dname in dirs:
                            try:
                                os.rmdir(os.path.join(root, dname))
                            except Exception:
                                pass
                    try:
                        os.rmdir(path)
                    except Exception:
                        pass
"""

with open("core/vector_store.py", "w", encoding="utf-8") as f:
    f.write(CONTENT)

print("Corregido: core/vector_store.py")
print("Ahora ejecuta: python tests/test_core_rag.py")
