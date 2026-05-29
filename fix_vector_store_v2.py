"""
Reescribe core/vector_store.py con API correcta para ChromaDB 1.0.9
Ejecutar desde rag_software_intelligence:
  python fix_vector_store_v2.py
"""
CONTENT = """\
import os
import gc
from typing import List, Optional
from langchain.schema import Document
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings


class VectorStoreManager:
    COLLECTION = "rag_software_intelligence"

    def __init__(self, persist_dir: str, model: str = "llama3.2"):
        self.persist_dir = persist_dir
        self.embeddings  = OllamaEmbeddings(model=model)
        self.store: Optional[Chroma] = None

    def build(self, documents: List[Document]) -> None:
        if not documents:
            raise ValueError("No hay documentos para indexar.")

        print("  [VectorStore] Indexando", len(documents), "chunks...")

        # Liberar conexion anterior
        if self.store is not None:
            try:
                del self.store
            except Exception:
                pass
            self.store = None
            gc.collect()

        # Limpiar directorio
        if os.path.exists(self.persist_dir):
            self._safe_rmtree(self.persist_dir)
        os.makedirs(self.persist_dir, exist_ok=True)

        # Indexar todo de una vez (mas estable que lotes con ChromaDB 1.x)
        batch_size = 40
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            if self.store is None:
                self.store = Chroma.from_documents(
                    documents=batch,
                    embedding=self.embeddings,
                    persist_directory=self.persist_dir,
                    collection_name=self.COLLECTION,
                )
            else:
                self.store.add_documents(batch)
            done = min(i + batch_size, len(documents))
            pct  = int(done / len(documents) * 100)
            print("    " + str(pct) + "% (" + str(done) + "/" + str(len(documents)) + ")")

        total = self._count_safe()
        print("  [VectorStore] Completado:", total, "vectores guardados en", self.persist_dir)

    def load_existing(self) -> bool:
        if not os.path.exists(self.persist_dir):
            return False
        try:
            self.store = Chroma(
                persist_directory=self.persist_dir,
                embedding_function=self.embeddings,
                collection_name=self.COLLECTION,
            )
            total = self._count_safe()
            print("  [VectorStore] Indice cargado:", total, "vectores")
            return total > 0
        except Exception as e:
            print("  [VectorStore] Error al cargar:", str(e))
            return False

    def search(self, query: str, k: int = 5) -> List[Document]:
        if self.store is None:
            raise RuntimeError("VectorStore no inicializado.")
        return self.store.similarity_search(query, k=k)

    def count(self) -> int:
        return self._count_safe()

    def _count_safe(self) -> int:
        if self.store is None:
            return 0
        # Intentar varias formas de contar segun la version de ChromaDB
        try:
            return self.store._collection.count()
        except Exception:
            pass
        try:
            result = self.store.get()
            return len(result.get("ids", []))
        except Exception:
            pass
        try:
            # Verificar con una busqueda simple
            test = self.store.similarity_search("inventario", k=1)
            return 1 if test else 0
        except Exception:
            return 0

    @staticmethod
    def _safe_rmtree(path: str) -> None:
        import shutil, time
        for _ in range(3):
            try:
                shutil.rmtree(path)
                return
            except PermissionError:
                time.sleep(1)
        # Borrar archivo por archivo
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

# Tambien arreglamos el pipeline para mostrar progreso real
PIPELINE = """\
import os
from typing import List
from langchain.schema import Document

from config.settings import (GITHUB_REPO_URL, CLONE_DIR,
                              CHROMA_PERSIST_DIR, OLLAMA_MODEL,
                              CHUNK_SIZE, CHUNK_OVERLAP, TOP_K_RESULTS)
from ingestors.git_loader    import GitLoader
from ingestors.drawio_loader import DrawioLoader
from ingestors.excel_loader  import ExcelLoader
from ingestors.doc_loader    import DocLoader
from core.chunker             import SmartChunker
from core.vector_store        import VectorStoreManager


class IngestionPipeline:
    UPLOADS_DIR = "data/uploads"

    def __init__(self):
        self.chunker      = SmartChunker(CHUNK_SIZE, CHUNK_OVERLAP)
        self.vector_store = VectorStoreManager(CHROMA_PERSIST_DIR, OLLAMA_MODEL)

    def run(self, force_rebuild: bool = False) -> int:
        if not force_rebuild and self.vector_store.load_existing():
            print("[Pipeline] Indice existente cargado:", self.vector_store.count(), "vectores")
            return self.vector_store.count()

        print("[Pipeline] Iniciando ingesta...")
        all_docs: List[Document] = []

        # Git
        if GITHUB_REPO_URL:
            try:
                docs = GitLoader(GITHUB_REPO_URL, CLONE_DIR).load()
                all_docs.extend(docs)
                print("[Pipeline] Git:", len(docs), "archivos")
            except Exception as e:
                print("[Pipeline] Error Git:", str(e))

        # Draw.io
        if os.path.exists(self.UPLOADS_DIR):
            for fname in os.listdir(self.UPLOADS_DIR):
                if fname.endswith(".drawio"):
                    try:
                        docs = DrawioLoader(os.path.join(self.UPLOADS_DIR, fname)).load()
                        all_docs.extend(docs)
                        print("[Pipeline] DrawIO:", len(docs), "elementos")
                    except Exception as e:
                        print("[Pipeline] Error DrawIO:", str(e))

        # Excel
        if os.path.exists(self.UPLOADS_DIR):
            for fname in os.listdir(self.UPLOADS_DIR):
                if fname.endswith(".xlsx"):
                    try:
                        docs = ExcelLoader(os.path.join(self.UPLOADS_DIR, fname)).load()
                        all_docs.extend(docs)
                        print("[Pipeline] Excel:", len(docs), "campos")
                    except Exception as e:
                        print("[Pipeline] Error Excel:", str(e))

        if not all_docs:
            print("[Pipeline] No se encontraron documentos.")
            return 0

        print("[Pipeline] Total:", len(all_docs), "documentos -> chunking...")
        chunks = self.chunker.chunk(all_docs)
        print("[Pipeline] Chunks generados:", len(chunks))

        self.vector_store.build(chunks)
        total = self.vector_store.count()
        print("[Pipeline] LISTO:", total, "vectores en ChromaDB")
        return total

    def get_vector_store(self) -> VectorStoreManager:
        return self.vector_store
"""

with open("core/pipeline.py", "w", encoding="utf-8") as f:
    f.write(PIPELINE)
print("Corregido: core/pipeline.py")
print("\nAhora:")
print("1. Ctrl+C en el PowerShell de Streamlit")
print("2. python fix_vector_store_v2.py ya lo hiciste")
print("3. streamlit run ui/app.py")
print("4. Clic en Indexar y espera")
