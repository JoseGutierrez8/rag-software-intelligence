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
